"""Characterizing tests for ``agentsparty.protocol.language.core``.

One algebraic law → one property (or one boundary example). Schema↔decode
commuting diagrams live in ``test_schema_decode.py``; raw totality in ``test_raw.py``.
"""

from __future__ import annotations

import inspect
import json
import math
from dataclasses import dataclass
from datetime import timedelta
from functools import reduce
from operator import rshift
from typing import cast

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from agentsparty.kernel.errors import PayloadError
from agentsparty.protocol.language.core import (
    Codec,
    Deadline,
    Flag,
    Fragment,
    Integer,
    Label,
    Nothing,
    Null,
    Number,
    Text,
    branches_map,
    case,
    codec_of,
    dict_of,
    json_model,
    list_of,
    load_json,
    one_of,
    optional,
    record,
    refine,
    selection_codec,
)
from agentsparty.protocol.session import SessionBranchCase, SessionEnd


@dataclass(frozen=True)
class FakeProto:
    name: str


END = FakeProto('end')


def frag(name: str) -> Fragment[FakeProto]:
    return Fragment(lambda tail: FakeProto(f'{name}({tail.name})'), END)


def identity() -> Fragment[FakeProto]:
    return Fragment.identity(END)


def halt() -> Fragment[FakeProto]:
    return Fragment.halt(END)


def _obs_eq(
    a: Fragment[FakeProto],
    b: Fragment[FakeProto],
    tails: list[FakeProto],
) -> bool:
    return all(a.fill(t) == b.fill(t) for t in tails) and a.close() == b.close()


@st.composite
def fragments(draw: st.DrawFn) -> Fragment[FakeProto]:
    kind = draw(st.sampled_from(['id', 'halt', 'wrap', 'compose']))
    if kind == 'id':
        return identity()
    if kind == 'halt':
        return halt()
    if kind == 'wrap':
        return frag(draw(st.sampled_from(['a', 'b', 'c', 'd'])))
    left = draw(fragments())
    right = draw(fragments())
    return left >> right


_TAILS = [FakeProto('t0'), FakeProto('t1'), FakeProto('z')]


@given(name=st.text())
def test_label_str_equals_name(name: str) -> None:
    assert str(Label(name)) == name


@given(a=st.text(), b=st.text())
def test_label_equality_iff_names_equal(a: str, b: str) -> None:
    assert (Label(a) == Label(b)) == (a == b)


@given(st.text())
def test_text_decode_is_identity(s: str) -> None:
    assert Text.decode(s) == s


@given(st.integers())
def test_integer_decode_on_int(n: int) -> None:
    assert Integer.decode(n) == n


@given(b=st.booleans())
def test_flag_decode_on_bool(*, b: bool) -> None:
    assert Flag.decode(b) is b


@given(
    st.one_of(
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        st.integers(min_value=-(10**6), max_value=10**6),
    ),
)
def test_number_decode_to_float(n: float) -> None:
    assert math.isclose(Number.decode(n), float(n))


def test_nothing_decode_none() -> None:
    assert Nothing.decode(None) is None


@given(st.lists(st.integers(), max_size=10))
def test_list_of_is_map(xs: list[int]) -> None:
    codec = list_of(Integer)
    assert codec.name == 'list[int]'
    assert codec.decode(xs) == [Integer.decode(x) for x in xs]


@given(st.dictionaries(st.text(max_size=5), st.integers(), max_size=5))
def test_dict_of_is_map(d: dict[str, int]) -> None:
    codec = dict_of(Integer)
    assert codec.name == 'dict[str, int]'
    assert codec.decode(d) == {k: Integer.decode(v) for k, v in d.items()}


@given(st.text())
def test_one_of_returns_first_matching_decode(raw: str) -> None:
    codec = one_of(Integer, Text)
    assert codec.name == 'int | str'
    if _looks_like_int(raw):
        assert codec.decode(raw) == Integer.decode(raw)
    else:
        assert codec.decode(raw) == raw


def _looks_like_int(s: str) -> bool:
    try:
        int(s.strip())
    except ValueError:
        return False
    return True


def test_one_of_all_fail() -> None:
    with pytest.raises(
        PayloadError,
        match=r'^payload does not match int \| float \| bool: expected bool payload',
    ):
        one_of(Integer, Number, Flag).decode('nope')


def test_one_of_requires_a_first_codec() -> None:
    assert inspect.signature(one_of).parameters['first'].default is inspect.Parameter.empty


@given(st.one_of(st.none(), st.text(max_size=20)))
def test_optional_preserves_present_and_absent_values(raw: str | None) -> None:
    assert optional(Text).decode(raw) == raw


@given(
    codec=st.sampled_from((Nothing, Null, Text, Integer, Number, Flag)),
    label=st.text(min_size=1),
    intent=st.text(),
)
def test_codec_call_is_case_with_codec(codec: Codec, label: str, intent: str) -> None:
    assume(label.strip())
    assert codec(label, intent) == case(label, codec, intent)


def test_codec_call_rejects_blank_label() -> None:
    with pytest.raises(AssertionError, match='label must not be blank'):
        Text('   ')


def test_codec_call_preserves_deadline() -> None:
    deadline = Deadline(timedelta(seconds=1))
    assert Text('Timed', within=deadline).within is deadline


def test_codec_constraint_names_follow_the_wire_contract() -> None:
    task = record('Task', name=str)

    assert task.many().name == 'list[Task]'
    assert task.many(1).name == 'list[Task] where at least 1 item'
    assert task.many(at_most=3).name == 'list[Task] where at most 3 items'
    assert task.many(1, 10).name == 'list[Task] where between 1 and 10 items'
    assert task.many(2, 2).name == 'list[Task] where exactly 2 items'
    assert Integer.between(1, 5).name == 'int where between 1 and 5'
    assert Text.mapping().having('id', 'sender').name == ('dict[str, str] where carries id, sender')
    assert Text.where('a note', lambda _: True).name == 'str where a note'
    assert Text.optional().name == optional(Text).name
    assert (Text | Integer).name == one_of(Text, Integer).name


def test_codec_constraint_decoding_is_closed_over_valid_values() -> None:
    bounded = Integer.many(1, 2)
    assert bounded.decode([1, 2]) == [1, 2]
    with pytest.raises(PayloadError):
        bounded.decode([])

    ranged = Integer.between(1, 5)
    assert ranged.decode(3) == 3
    with pytest.raises(PayloadError):
        ranged.decode(6)

    carrying = Text.mapping().having('id', 'sender')
    assert carrying.decode({'id': '1', 'sender': 'A'}) == {'id': '1', 'sender': 'A'}
    with pytest.raises(PayloadError):
        carrying.decode({'id': '1'})


def test_codec_constraint_preconditions_are_rejected() -> None:
    with pytest.raises(ValueError, match='at_least must be non-negative'):
        Text.many(-1)
    with pytest.raises(AssertionError, match='at_least must not exceed at_most'):
        Text.many(5, 2)
    with pytest.raises(AssertionError, match='low must not exceed high'):
        Integer.between(5, 1)
    assert inspect.signature(Text.having).parameters['first'].default is inspect.Parameter.empty


def test_json_model_decode() -> None:
    codec = json_model(
        'Item',
        {'type': 'object', 'properties': {'x': {'type': 'integer'}}},
        json.loads,
    )
    assert codec.name == 'Item'
    assert dict(codec.schema) == {
        'type': 'object',
        'properties': {'x': {'type': 'integer'}},
    }
    assert codec.decode({'x': 1}) == {'x': 1}
    assert codec.decode('{"x": 1}') == {'x': 1}


def test_codec_of_resolves_container_annotations() -> None:
    list_codec = codec_of(list[int])
    dict_codec = codec_of(dict[str, int])

    assert list_codec.name == 'list[int]'
    assert list_codec.decode([1, 2]) == [1, 2]
    assert dict_codec.name == 'dict[str, int]'
    assert dict_codec.decode({'x': 1}) == {'x': 1}


@pytest.mark.parametrize('annotation', [tuple[int], tuple[str, int], dict[int, str]])
def test_codec_of_rejects_unsupported_container_annotations(annotation: object) -> None:
    with pytest.raises(TypeError, match=r'^unsupported annotation'):
        codec_of(annotation)


def test_json_model_parse_failure() -> None:
    def boom(_s: str) -> object:
        raise RuntimeError('bad')

    codec = json_model('X', {'type': 'object'}, boom)
    with pytest.raises(PayloadError, match='payload does not match X'):
        codec.decode({})


def test_golden_schemas() -> None:
    assert dict(Nothing.schema) == {'type': 'null'}
    assert dict(Null.schema) == {'type': 'null'}
    assert dict(Text.schema) == {'type': 'string'}
    assert dict(Integer.schema) == {'type': 'integer'}
    assert dict(Number.schema) == {'type': 'number'}
    assert dict(Flag.schema) == {'type': 'boolean'}
    assert dict(list_of(Integer).schema) == {
        'type': 'array',
        'items': {'type': 'integer'},
    }
    assert dict(dict_of(Flag).schema) == {
        'type': 'object',
        'additionalProperties': {'type': 'boolean'},
    }
    assert dict(one_of(Text, Integer).schema) == {
        'anyOf': [{'type': 'string'}, {'type': 'integer'}],
    }


@given(f=fragments(), g=fragments(), h=fragments())
def test_fragment_associativity(
    f: Fragment[FakeProto],
    g: Fragment[FakeProto],
    h: Fragment[FakeProto],
) -> None:
    assert _obs_eq((f >> g) >> h, f >> (g >> h), _TAILS)


@given(f=fragments())
def test_fragment_left_identity(f: Fragment[FakeProto]) -> None:
    assert _obs_eq(identity() >> f, f, _TAILS)


@given(f=fragments())
def test_fragment_right_identity(f: Fragment[FakeProto]) -> None:
    assert _obs_eq(f >> identity(), f, _TAILS)


@given(f=fragments())
def test_fragment_halt_left_zero(f: Fragment[FakeProto]) -> None:
    assert _obs_eq(halt() >> f, halt(), _TAILS)


def test_case_body_first_attach() -> None:
    c = case('a', Text) >> frag('f')
    assert c.body is not None
    assert _obs_eq(c.body, frag('f'), _TAILS)


def test_case_body_composition() -> None:
    c = case('a') >> frag('f') >> frag('g')
    assert c.body is not None
    assert _obs_eq(c.body, frag('f') >> frag('g'), _TAILS)


@given(steps=st.lists(fragments(), min_size=1, max_size=4))
def test_case_then_is_the_rshift_chain(steps: list[Fragment[FakeProto]]) -> None:
    first, *rest = steps
    composed = case('a', Text).then(first, *rest)  # type: ignore[arg-type]
    chained = reduce(rshift, steps, case('a', Text))
    assert composed.body is not None
    assert chained.body is not None
    assert _obs_eq(composed.body, chained.body, _TAILS)


def test_case_accepts_string_and_label() -> None:
    string_case = case('hello', Text)
    assert string_case.label == Label('hello')
    assert string_case.payload is Text
    lbl = Label('hello')
    assert case(lbl).label == lbl


def test_case_preserves_deadline() -> None:
    deadline = Deadline(timedelta(seconds=1))

    assert case('hello', Text, within=deadline).within is deadline


def test_case_rejects_invalid_label() -> None:
    with pytest.raises(TypeError, match=r'^expected a label or string, got 42$'):
        case(cast(str, 42))


def test_branches_map_duplicate_labels_raise() -> None:
    with pytest.raises(ValueError, match='duplicate key'):
        branches_map([case('a'), case('a')])


def test_branches_map_keys_from_labels() -> None:
    @dataclass(frozen=True)
    class Br:
        label: Label

    a, b = Br(Label('a')), Br(Label('b'))
    result = branches_map([a, b])
    assert result[Label('a')] is a
    assert result[Label('b')] is b


@dataclass(frozen=True, slots=True)
class _Br:
    label: Label
    payload: Codec[object]
    intent: str = ''


_RAW_BY_CODEC: dict[str, object] = {
    'undefined': None,
    'null': None,
    'str': 'x',
    'int': 1,
    'float': 1.5,
    'bool': True,
}


@given(codec=st.sampled_from((Nothing, Null, Text, Integer, Number, Flag)))
def test_selection_codec_keeps_raw_that_decodes_to_the_payload(codec) -> None:
    branch = SessionBranchCase(Label('only'), codec, SessionEnd())
    branches = branches_map([branch])
    raw = _RAW_BY_CODEC[codec.name]
    text = json.dumps({'alt': {'label': 'only', 'payload': raw}})
    chosen = selection_codec(branches).decode(load_json(text))
    assert chosen.branch.payload.decode(chosen.raw) == chosen.payload


def test_selection_codec_unknown_label() -> None:
    branches = branches_map([_Br(Label('Order'), Text), _Br(Label('Quit'), Nothing)])
    with pytest.raises(PayloadError, match=r"unknown label 'Nope'; expected: Order, Quit"):
        selection_codec(branches).decode({'alt': {'label': 'Nope', 'payload': 'x'}})


def test_selection_codec_missing_fields() -> None:
    codec = selection_codec(branches_map([_Br(Label('Order'), Text)]))
    with pytest.raises(PayloadError, match=r'^model output must match the Choice schema$'):
        codec.decode({})
    with pytest.raises(PayloadError, match=r'^model output must match the Choice schema$'):
        codec.decode({'alt': {}})
    with pytest.raises(PayloadError, match=r'^model output must match the Choice schema$'):
        codec.decode({'alt': {'label': 'Order'}})


def test_golden_selection_schema() -> None:
    order = _Br(Label('Order'), Text)
    quit_ = _Br(Label('Quit'), Nothing)
    codec = selection_codec(branches_map([order, quit_]))
    assert codec.name == 'alt'
    schema = dict(codec.schema)
    expected = {
        'type': 'object',
        'properties': {
            'alt': {
                'anyOf': [
                    {
                        'type': 'object',
                        'properties': {
                            'label': {'type': 'string', 'enum': ['Order']},
                            'payload': {'type': 'string'},
                        },
                        'required': ['label', 'payload'],
                        'additionalProperties': False,
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'label': {'type': 'string', 'enum': ['Quit']},
                            'payload': {'type': 'null'},
                        },
                        'required': ['label', 'payload'],
                        'additionalProperties': False,
                    },
                ],
            },
        },
        'required': ['alt'],
        'additionalProperties': False,
    }
    assert schema == expected


@given(intent=st.text(), name=st.sampled_from(['a', 'b', 'c']))
def test_a_case_keeps_its_intent_through_composition(intent: str, name: str) -> None:
    fragment = frag(name)
    composed = case('Hi', Text, intent) >> fragment  # type: ignore[operator]
    assert composed.intent == intent


def test_a_case_without_intent_is_the_empty_text() -> None:
    assert not case('Hi').intent


@given(text=st.text())
def test_a_trivial_refinement_is_the_codec(text: str) -> None:
    refined = refine(Text, 'anything', lambda _: True)
    assert refined.decode(text) == Text.decode(text)


@given(text=st.text())
def test_a_refinement_only_accepts_what_holds(text: str) -> None:
    holds = lambda value: len(value) <= 3  # noqa: E731
    refined = refine(Text, 'at most 3 chars', holds)
    if holds(text):
        assert refined.decode(text) == text
        assert holds(refined.decode(text))
    else:
        with pytest.raises(PayloadError, match='at most 3 chars'):
            refined.decode(text)


@given(text=st.text())
def test_a_refinement_composes(text: str) -> None:
    p1 = lambda value: len(value) >= 2  # noqa: E731
    p2 = lambda value: 'x' in value  # noqa: E731
    nested = refine(refine(Text, 'len>=2', p1), 'has x', p2)
    if p1(text) and p2(text):
        assert nested.decode(text) == text
    else:
        with pytest.raises(PayloadError):
            nested.decode(text)


def test_a_refinement_renames_the_codec() -> None:
    assert (
        refine(Text, 'under 200 words', lambda s: len(s.split()) < 200).name
        == 'str where under 200 words'
    )


def test_a_refinement_keeps_the_schema() -> None:
    refined = refine(Text, 'non-empty', bool)
    assert refined.schema == Text.schema
    assert refined.carries_value is True


def test_a_blank_requirement_is_refused() -> None:
    with pytest.raises(ValueError, match=r'^a refinement must state its requirement$'):
        refine(Text, '   ', lambda _: True)


def test_the_requirement_is_in_the_error() -> None:
    with pytest.raises(PayloadError, match='under 200 words'):
        refine(Text, 'under 200 words', lambda _: False).decode('x')
