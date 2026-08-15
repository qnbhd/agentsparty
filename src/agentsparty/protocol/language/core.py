"""Protocol building blocks: ``Codec``, ``Fragment``, ``Case``, selection."""

from __future__ import annotations

import types as _stdlib_types
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from functools import partial, reduce
from typing import Any, Final, Generic, Protocol, TypeVar, get_args, get_origin

from agentsparty._utils.assertions import post, require_nonnegative, safe_assert
from agentsparty.kernel.errors import PayloadError
from agentsparty.kernel.nonempty import NonEmptyMap, NonEmptyTuple
from agentsparty.protocol.language.raw import (
    RawValue,
    as_array,
    as_flag,
    as_integer,
    as_json_text,
    as_nothing,
    as_null,
    as_number,
    as_object,
    as_text,
    load_json,
)

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)

_TYPE_KEY: Final = 'type'
_OBJECT_TYPE: Final = 'object'
_ADDITIONAL_PROPERTIES_KEY: Final = 'additionalProperties'
_CHOICE_KEY: Final = 'alt'
_LABEL_KEY: Final = 'label'
_PAYLOAD_KEY: Final = 'payload'
_NULL_SCHEMA: Mapping[str, object] = _stdlib_types.MappingProxyType({_TYPE_KEY: 'null'})


@dataclass(frozen=True, slots=True)
class Codec(Generic[T_co]):
    """Everything the protocol knows about a branch payload — as data.

    ``decode`` must be pure: journalled sessions replay a payload by decoding
    the raw form again, and that has to yield the same value.
    """

    name: str
    schema: Mapping[str, object]
    decode: Callable[[RawValue], T_co]
    carries_value: bool = True

    def __call__(
        self,
        label: str | Label,
        intent: str = '',
        *,
        within: Deadline | None = None,
    ) -> Case[Any]:
        """Construct this codec's branch under *label*."""
        parsed_label = _as_label(label)
        label_text = parsed_label.name
        safe_assert(expr=bool(label_text.strip()), message='a label must not be blank')
        built = case(parsed_label, self, intent, within=within)
        post(expr=built.payload is self, message='a codec branch must keep its codec')
        post(expr=built.label == parsed_label, message='a codec branch must keep its label')
        return built

    def many(
        self,
        at_least: int | None = None,
        at_most: int | None = None,
    ) -> Codec[list[T_co]]:
        """A list of this codec's values, optionally bounded in length."""
        if at_least is not None:
            require_nonnegative('at_least', at_least)
        if at_most is not None:
            require_nonnegative('at_most', at_most)
        if at_least is not None and at_most is not None:
            safe_assert(expr=at_least <= at_most, message='at_least must not exceed at_most')
        codec = list_of(self)
        if at_least is None and at_most is None:
            return codec
        requirement = _size_requirement(at_least, at_most)
        return refine(codec, requirement, partial(_has_size, at_least, at_most))

    def mapping(self) -> Codec[dict[str, T_co]]:
        """A string-keyed mapping of this codec's values."""
        return dict_of(self)

    def between(self, low: float, high: float) -> Codec[T_co]:
        """Values of this codec that lie in the closed range ``[low, high]``."""
        safe_assert(expr=low <= high, message='low must not exceed high')
        requirement = _range_requirement(low, high)
        holds = partial(_in_range, low, high)
        return refine(self, requirement, holds)

    def having(self, first: str, /, *rest: str) -> Codec[T_co]:
        """Objects of this codec that carry at least the named keys."""
        keys = (first, *rest)
        safe_assert(expr=all(key.strip() for key in keys), message='keys must not be blank')
        requirement = 'carries {}'.format(', '.join(keys))
        holds = partial(_carries, keys)
        return refine(self, requirement, holds)

    def where(self, requirement: str, holds: Callable[[T_co], bool]) -> Codec[T_co]:
        """Values of this codec satisfying *holds*."""
        return refine(self, requirement, holds)

    def optional(self) -> Codec[T_co | None]:
        """Values of this codec or JSON ``null``."""
        return optional(self)

    def __or__(self, other: Codec[Any]) -> Codec[Any]:
        """A codec accepting values decoded by either operand."""
        return one_of(self, other)


def _schema(mapping: dict[str, object]) -> Mapping[str, object]:
    return _stdlib_types.MappingProxyType(mapping)


Nothing: Codec[None] = Codec(
    name='undefined',
    schema=_NULL_SCHEMA,
    decode=as_nothing,
    carries_value=False,
)
Null: Codec[None] = Codec(name='null', schema=_NULL_SCHEMA, decode=as_null)
Text: Codec[str] = Codec(
    name='str',
    schema=_schema({_TYPE_KEY: 'string'}),
    decode=as_text,
)
Integer: Codec[int] = Codec(
    name='int',
    schema=_schema({_TYPE_KEY: 'integer'}),
    decode=as_integer,
)
Number: Codec[float] = Codec(
    name='float',
    schema=_schema({_TYPE_KEY: 'number'}),
    decode=as_number,
)
Flag: Codec[bool] = Codec(
    name='bool',
    schema=_schema({_TYPE_KEY: 'boolean'}),
    decode=as_flag,
)


def _decode_list(item: Codec[T], raw: RawValue) -> list[T]:
    entries = as_array(raw)
    return [item.decode(entry) for entry in entries]


def _decode_dict(value: Codec[T], raw: RawValue) -> dict[str, T]:
    values = as_object(raw)
    return {key: value.decode(entry) for key, entry in values.items()}


def _decode_one_of(codecs: tuple[Codec[Any], ...], raw: RawValue) -> object:
    decoded, last = _try_all(codecs, raw)
    if last is None:
        return decoded
    names = ' | '.join(codec.name for codec in codecs)
    raise PayloadError(f'payload does not match {names}: {last}') from last


def _try_all(
    codecs: tuple[Codec[Any], ...],
    raw: RawValue,
) -> tuple[object, PayloadError | None]:
    errors: list[PayloadError] = []
    for codec in codecs:
        decoded, error = _try_decode(codec, raw)
        if error is None:
            return decoded, None
        errors.append(error)
    safe_assert(expr=bool(errors))
    return None, errors[-1]


def _try_decode(codec: Codec[Any], raw: RawValue) -> tuple[object, PayloadError | None]:
    try:
        return codec.decode(raw), None
    except PayloadError as exc:
        return raw, exc


def _decode_refined(
    codec: Codec[T],
    requirement: str,
    holds: Callable[[T], bool],
    raw: RawValue,
) -> T:
    value = codec.decode(raw)
    if not holds(value):
        raise PayloadError(f'payload does not satisfy {requirement}')
    return value


def _decode_json_model(name: str, parse: Callable[[str], T], raw: RawValue) -> T:
    text = as_json_text(raw)
    try:
        return parse(text)
    except Exception as exc:
        raise PayloadError(f'payload does not match {name}: {exc}') from exc


def _decode_record(
    title: str,
    codecs: Mapping[str, Codec[Any]],
    raw: RawValue,
) -> dict[str, Any]:
    data = as_object(raw)
    missing = [key for key in codecs if key not in data]
    if missing:
        raise PayloadError(f'{title}: missing fields {missing}')
    return {key: _decode_record_field(key, codec, data) for key, codec in codecs.items()}


def _decode_record_field(key: str, codec: Codec[T], data: Mapping[str, RawValue]) -> T:
    return codec.decode(data[key])


def list_of(item: Codec[T]) -> Codec[list[T]]:
    """A :class:`Codec` for a JSON array whose entries decode with *item*.

    Args:
        item: The codec applied to every array element.
    """
    codec_name = f'list[{item.name}]'
    return Codec(
        name=codec_name,
        schema=_schema({_TYPE_KEY: 'array', 'items': dict(item.schema)}),
        decode=partial(_decode_list, item),
    )


def dict_of(value: Codec[T]) -> Codec[dict[str, T]]:
    """A :class:`Codec` for a JSON object whose values decode with *value*.

    Args:
        value: The codec applied to every object value.
    """
    return Codec(
        name=f'dict[str, {value.name}]',
        schema=_schema(
            {
                _TYPE_KEY: _OBJECT_TYPE,
                _ADDITIONAL_PROPERTIES_KEY: dict(value.schema),
            },
        ),
        decode=partial(_decode_dict, value),
    )


def one_of(first: Codec[Any], *rest: Codec[Any]) -> Codec[Any]:
    """A :class:`Codec` that tries each of *codecs* in order.

    Args:
        first: The first alternative to attempt.
        *rest: Remaining alternatives to attempt, first match wins.
    """
    codecs = (first, *rest)

    return Codec(
        name=' | '.join(c.name for c in codecs),
        schema=_schema({'anyOf': [dict(c.schema) for c in codecs]}),
        decode=partial(_decode_one_of, codecs),
    )


def optional(codec: Codec[T]) -> Codec[T | None]:
    """A :class:`Codec` that accepts either *codec* or JSON ``null``.

    Args:
        codec: The codec used when the payload is not null.
    """
    return one_of(codec, Null)  # type: ignore[return-value]


def refine(
    codec: Codec[T],
    requirement: str,
    holds: Callable[[T], bool],
) -> Codec[T]:
    """A :class:`Codec` that accepts only values of *codec* satisfying *holds*.

    What the industry calls a task guardrail is this and nothing else: a pure
    predicate on the payload belongs to the type, so a value that leaves
    ``decode`` is correct by construction and nothing downstream re-checks it.

    *requirement* does three jobs at once, which is why it is not optional: it
    names the refined codec (so a journal written under the old codec is
    refused by ``Decision.branch_in`` instead of replaying into the wrong
    session), it is the diagnosis in the raised :exc:`PayloadError`, and — via
    that error — it is the feedback :class:`~agentsparty.agent.Repair` sends back to
    the model.

    *holds* must be pure and total: it is called again on replay, and a
    predicate that raises is a bug in the caller, not a rejected payload.

    The schema is left untouched. It states the *shape* the provider must
    validate; a requirement it cannot enforce does not belong in it. What the
    author wants produced is said once, in the branch's ``intent``.

    Args:
        codec: The codec being refined.
        requirement: The requirement, in the words a model should read.
        holds: The predicate every accepted value must satisfy.

    Returns:
        The refined codec.

    Raises:
        ValueError: if *requirement* is blank.
    """
    if not requirement.strip():
        raise ValueError('a refinement must state its requirement')

    return Codec(
        name=f'{codec.name} where {requirement}',
        schema=codec.schema,
        decode=partial(_decode_refined, codec, requirement, holds),
        carries_value=codec.carries_value,
    )


def _size_requirement(at_least: int | None, at_most: int | None) -> str:
    """Describe a bounded collection size with deterministic grammar."""
    if at_least is not None and at_most is not None and at_least == at_most:
        return f'exactly {at_least} {_size_noun(at_least)}'
    if at_least is not None and at_most is not None:
        return f'between {at_least} and {at_most} {_size_noun(at_most)}'
    if at_least is not None:
        return f'at least {at_least} {_size_noun(at_least)}'
    safe_assert(expr=at_most is not None, message='a size requirement needs a bound')
    if at_most is None:
        raise AssertionError('a size requirement needs a bound')
    return f'at most {at_most} {_size_noun(at_most)}'


def _size_noun(size: int) -> str:
    """Return the singular or plural noun for a size."""
    return 'item' if size == 1 else 'items'


def _range_requirement(low: float, high: float) -> str:
    """Return a numeric range in the codec requirement grammar."""
    return 'between {} and {}'.format(format(low, 'g'), format(high, 'g'))


def _has_size(
    at_least: int | None,
    at_most: int | None,
    values: Any,
) -> bool:
    """Return whether *values* lies within the requested size bounds."""
    size = len(values)
    meets_lower = at_least is None or at_least <= size
    meets_upper = at_most is None or size <= at_most
    return meets_lower and meets_upper


def _in_range(low: float, high: float, value: Any) -> bool:
    """Return whether *value* lies in the closed numeric range."""
    return low <= value <= high


def _carries(keys: tuple[str, ...], value: Any) -> bool:
    """Return whether an object contains every required key."""
    return all(key in value for key in keys)


def json_model(
    name: str,
    schema: Mapping[str, object],
    parse: Callable[[str], T],
) -> Codec[T]:
    """Codec for a framework model that owns its JSON schema and parser."""
    schema_values = {str(key): value for key, value in schema.items()}
    schema_map = _schema(schema_values)

    return Codec(
        name=name,
        schema=schema_map,
        decode=partial(_decode_json_model, name, parse),
    )


_PRIMITIVE_CODECS: Mapping[object, Codec[Any]] = _stdlib_types.MappingProxyType(
    {
        str: Text,
        int: Integer,
        float: Number,
        bool: Flag,
        type(None): Nothing,
        None: Nothing,  # codec_of(None) — annotation form for "no payload"
    },
)

_SUPPORTED_FORMS = 'str, int, float, bool, None, list[T], dict[str, T], a Codec, or record(...)'


def codec_of(annotation: object) -> Codec[Any]:
    """Resolve a Python annotation or :class:`Codec` to a payload codec.

    This is the single parse boundary for type annotations. Supported forms
    are the primitive registry, ``list[T]``, ``dict[str, T]``, an existing
    :class:`Codec`, and values built by :func:`record`. Everything else is a
    hard :exc:`TypeError` — no guessing, no pydantic/msgspec reflection.

    Args:
        annotation: A supported annotation, or an already-built codec.

    Returns:
        The codec for *annotation*.

    Raises:
        TypeError: if *annotation* is not a supported form.
    """
    codec = _codec_if_ready(annotation)
    if codec is not None:
        return codec
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list and len(args) == 1:
        return list_of(codec_of(args[0]))
    is_dict_form = origin is dict and len(args) == 2
    if is_dict_form and args[0] is str:
        return dict_of(codec_of(args[1]))
    raise TypeError(
        f'unsupported annotation {annotation!r}; supported forms: {_SUPPORTED_FORMS}',
    )


def _codec_if_ready(annotation: object) -> Codec[Any] | None:
    """Return *annotation* when it is already a codec or a known primitive."""
    match annotation:
        case Codec() as codec:
            return codec
        case _:
            return _PRIMITIVE_CODECS.get(annotation)


def record(title: str, /, **fields: object) -> Codec[dict[str, Any]]:
    """A closed object codec: fixed string keys, ``additionalProperties: false``.

    Each field value is resolved with :func:`codec_of`. The resulting schema
    lists every key as required and rejects extras — what strict provider
    modes demand of structured output. *title* is positional-only so a field
    may itself be named ``name``.

    Args:
        title: The codec name (also the schema title for diagnostics).
        **fields: Field name to annotation or codec.

    Returns:
        A codec that decodes a JSON object into ``dict[str, Any]``.

    Raises:
        ValueError: if no fields are given.
        TypeError: if a field annotation is not a supported form.
    """
    if not fields:
        raise ValueError('record requires at least one field')
    codecs = {key: codec_of(annotation) for key, annotation in fields.items()}
    schema = _schema(
        {
            _TYPE_KEY: 'object',
            'properties': {key: dict(codec.schema) for key, codec in codecs.items()},
            'required': list(codecs),
            'additionalProperties': False,
        },
    )

    return Codec(
        name=title,
        schema=schema,
        decode=partial(_decode_record, title, codecs),
    )


@dataclass(frozen=True, order=True, slots=True)
class Label:
    """A named branch label; frozen and orderable."""

    name: str

    def __str__(self) -> str:
        """Return the label's :attr:`name`."""
        return self.name


def _as_label(name: str | Label) -> Label:
    match name:
        case Label() as label:
            return label
        case str() as text:
            return Label(text)
        case _:
            raise TypeError(f'expected a label or string, got {name!r}')


P = TypeVar('P')


@dataclass(frozen=True, slots=True)
class Fragment(Generic[P]):
    """A protocol expression with a hole in its tail."""

    _fill: Callable[[P], P]
    _end: P

    def __rshift__(self, other: Fragment[P]) -> Fragment[P]:
        """Sequence this fragment before *other*.

        Args:
            other: The fragment that fills this one's hole.
        """
        return Fragment(lambda tail: self._fill(other.fill(tail)), self._end)

    def fill(self, tail: P) -> P:
        """Close the hole with *tail* and return the completed protocol.

        Args:
            tail: The continuation to close the hole with.
        """
        return self._fill(tail)

    def close(self) -> P:
        """Close the hole with the fragment's own end."""
        return self._fill(self._end)

    @classmethod
    def identity(cls, end: P) -> Fragment[P]:
        """A fragment that passes *tail* through unchanged.

        Args:
            end: The fragment's end value.
        """
        return cls(lambda tail: tail, end)

    @classmethod
    def halt(cls, end: P) -> Fragment[P]:
        """A fragment that ignores its tail and yields ``end`` (``stop``)."""
        return cls(lambda _tail: end, end)


@dataclass(frozen=True, slots=True)
class Deadline:
    """A strictly positive wall-clock window for one alt."""

    duration: timedelta

    def __post_init__(self) -> None:
        """Reject a window that cannot give the sender time to choose."""
        if self.duration.total_seconds() <= 0:
            raise ValueError('a deadline must be a positive duration')

    def total_seconds(self) -> float:
        """Return the window in seconds for the scheduler."""
        return self.duration.total_seconds()


@dataclass(frozen=True, slots=True)
class Case(Generic[P]):
    """One labelled alternative, shared by the global and local DSLs."""

    label: Label
    payload: Codec[Any] = Nothing
    body: Fragment[P] | None = None
    intent: str = ''
    within: Deadline | None = None

    def __rshift__(self, other: Fragment[P]) -> Case[P]:
        """Attach *other* as this case's continuation.

        Args:
            other: The fragment to append to this case's body.
        """
        if self.body is None:
            return Case(self.label, self.payload, other, self.intent, self.within)
        return Case(
            self.label,
            self.payload,
            self.body >> other,
            self.intent,
            self.within,
        )

    def then(self, first: Fragment[P], *rest: Fragment[P]) -> Case[P]:
        """This case followed by *first* and *rest*, in order.

        Equivalent to ``self >> first >> ...``, but the call brackets delimit
        the branch: in a multi-arm :func:`~agentsparty.protocol.session.alt`, the
        steps of a long arm are indented under their label instead of lining up
        with the next arm, which reads as one arm per parenthesised block.

        Args:
            first: The step that follows this case's label.
            *rest: Further steps, in the order they happen.

        Returns:
            This case with the steps appended to its body.
        """
        composed = seq(first, *rest)
        attached = self >> composed
        post(expr=attached.body is not None, message='then must attach a continuation')
        return attached


def case(
    label: str | Label,
    payload: Codec[Any] | type[Any] | object = Nothing,
    intent: str = '',
    *,
    within: Deadline | None = None,
) -> Case[Any]:
    """A labelled case with an optional payload codec, intent, and deadline.

    Args:
        label: The branch label, as text or a :class:`Label`.
        payload: The codec for the payload, or a supported annotation resolved
            by :func:`codec_of` (e.g. ``str``, ``list[str]``). Defaults to
            :data:`Nothing`.
        intent: What the sender is asked to produce on this branch, in one or
            two sentences. It is shown to whoever authors the message — a model
            or a person — and it is part of the protocol, so it enters
            :func:`~agentsparty.protocol.render.render` and therefore the journal
            digest. Absence is the empty text, not ``None``.
        within: Optional wall-clock window the sender has to choose this
            interaction. When set, it enters ``render`` / the journal digest
            and the runtime enforces it with ``asyncio.wait_for`` on
            ``select``. Absence is ``None`` (no deadline), not zero.
    """
    return Case(_as_label(label), codec_of(payload), intent=intent, within=within)


def _bodies(cases: NonEmptyTuple[Case[P]]) -> tuple[Case[P], ...]:
    """Return the declared cases; branch-map construction owns uniqueness."""
    return cases


def _continuation(body: Fragment[P] | None, tail: P, end: P) -> P:
    if body is None:
        return tail
    return body.fill(tail)


class Labelled(Protocol):
    """Anything that carries a :class:`Label`."""

    @property
    def label(self) -> Label:
        """The object's label."""
        ...


class BranchCodec(Labelled, Protocol):
    """A labelled branch that carries a payload codec and an intent."""

    @property
    def payload(self) -> Codec[Any]:
        """The codec for this branch's payload."""
        ...

    @property
    def intent(self) -> str:
        """What the sender is asked to produce on this branch; ``""`` if unsaid."""
        ...


B = TypeVar('B', bound=Labelled)
BC = TypeVar('BC', bound=BranchCodec)


def branches_map(branches: Iterable[B]) -> NonEmptyMap[Label, B]:
    """Build a branch map; keys are derived from each branch's label."""
    return NonEmptyMap.of_pairs((branch.label, branch) for branch in branches)


@dataclass(frozen=True, slots=True)
class Chosen(Generic[B]):
    """Selected branch, its decoded payload, and the raw form behind it.

    Invariant: ``branch.payload.decode(raw) == payload``. The raw form is what
    the participant authored — model JSON, a typed line, a scripted value — and
    it is what a journal records, so a later process can decode the same
    payload from the codec the protocol declares.
    """

    branch: B
    payload: object
    raw: RawValue


def _decode_selection(by_name: Mapping[str, BC], raw: RawValue) -> Chosen[BC]:
    root = as_object(raw)
    if _CHOICE_KEY not in root:
        raise PayloadError('model output must match the Choice schema')
    chosen = as_object(root[_CHOICE_KEY])
    if _LABEL_KEY not in chosen:
        raise PayloadError('model output must match the Choice schema')
    label_text = as_text(chosen[_LABEL_KEY])
    branch = _selection_branch(by_name, label_text)
    if _PAYLOAD_KEY not in chosen:
        raise PayloadError('model output must match the Choice schema')
    raw_payload = chosen[_PAYLOAD_KEY]
    return Chosen(
        branch=branch,
        payload=branch.payload.decode(raw_payload),
        raw=raw_payload,
    )


def _selection_branch(by_name: Mapping[str, BC], label_text: str) -> BC:
    branch = by_name.get(label_text)
    if branch is None:
        names = ', '.join(by_name)
        raise PayloadError(
            f'agent chose unknown label {label_text!r}; expected: {names}',
        )
    return branch


def selection_codec(branches: NonEmptyMap[Label, BC]) -> Codec[Chosen[BC]]:
    """Schema and decoder for a structured alt over *branches* (one parse)."""
    by_name = {str(branch.label): branch for branch in branches.values()}
    ordered = sorted(branches.values(), key=lambda b: b.label)

    arms: list[dict[str, object]] = [
        {
            _TYPE_KEY: _OBJECT_TYPE,
            'properties': {
                _LABEL_KEY: {_TYPE_KEY: 'string', 'enum': [str(branch.label)]},
                _PAYLOAD_KEY: dict(branch.payload.schema),
            },
            'required': [_LABEL_KEY, _PAYLOAD_KEY],
            _ADDITIONAL_PROPERTIES_KEY: False,
        }
        for branch in ordered
    ]
    alt_schema: dict[str, object] = arms[0] if len(arms) == 1 else {'anyOf': arms}
    schema = _schema(
        {
            _TYPE_KEY: _OBJECT_TYPE,
            'properties': {_CHOICE_KEY: alt_schema},
            'required': [_CHOICE_KEY],
            _ADDITIONAL_PROPERTIES_KEY: False,
        },
    )

    return Codec(
        name=_CHOICE_KEY,
        schema=schema,
        decode=partial(_decode_selection, by_name),
    )


def seq(first: Fragment[P], *rest: Fragment[P]) -> Fragment[P]:
    """Sequence *first* with *rest*, left to right.

    Args:
        first: The fragment to run first.
        *rest: Fragments to run after, in order.
    """
    from operator import rshift

    return reduce(rshift, rest, first)


def repeat(times: int, fragment: Fragment[P]) -> Fragment[P]:
    """Unroll *fragment* a fixed number of times (finite, not recursive).

    For true unbounded loops use :func:`~agentsparty.protocol.session.rec` /
    :func:`~agentsparty.protocol.session.var` on session protocols.
    """
    require_nonnegative('times', times)
    if times == 0:
        return Fragment.identity(fragment._end)
    return seq(*(fragment for _ in range(times)))


# Re-export raw surface used by callers
__all__ = [
    'BranchCodec',
    'Case',
    'Chosen',
    'Codec',
    'Deadline',
    'Flag',
    'Fragment',
    'Integer',
    'Label',
    'Nothing',
    'Null',
    'Number',
    'RawValue',
    'Text',
    'case',
    'codec_of',
    'dict_of',
    'json_model',
    'list_of',
    'load_json',
    'one_of',
    'optional',
    'record',
    'refine',
    'repeat',
    'seq',
]
