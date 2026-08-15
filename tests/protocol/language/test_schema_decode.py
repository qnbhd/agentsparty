"""Schema↔decode consistency: values valid under codec.schema decode without PayloadError.

One property per built-in/combinator (AGENTS.md: one law → one property).
Strategies generate RawValues that inhabit the JSON Schema each codec advertises.
"""

from __future__ import annotations

from dataclasses import dataclass

from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.protocol.language.core import (
    Codec,
    Flag,
    Integer,
    Label,
    Nothing,
    Null,
    Number,
    Text,
    branches_map,
    dict_of,
    list_of,
    one_of,
    optional,
    selection_codec,
)
from agentsparty.protocol.language.raw import RawValue

# Values valid for each advertised schema (JSON Schema type tags).
# bool is excluded from integer/number generators: JSON Schema separates them,
# and our perimeter rejects bool for as_integer/as_number.


@given(st.text(max_size=40))
def test_text_schema_values_decode(value: str) -> None:
    Text.decode(value)


@given(st.integers(min_value=-(10**9), max_value=10**9))
def test_integer_schema_values_decode(value: int) -> None:
    Integer.decode(value)


@given(
    st.one_of(
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        st.integers(min_value=-(10**6), max_value=10**6),
    ),
)
def test_number_schema_values_decode(value: float) -> None:
    Number.decode(value)


@given(value=st.booleans())
def test_flag_schema_values_decode(*, value: bool) -> None:
    Flag.decode(value)


def test_null_schema_value_decodes() -> None:
    Null.decode(None)


def test_nothing_schema_value_decodes() -> None:
    Nothing.decode(None)


@given(st.lists(st.integers(min_value=-(10**6), max_value=10**6), max_size=8))
def test_list_of_integer_schema_values_decode(value: list[int]) -> None:
    list_of(Integer).decode(value)


@given(
    st.dictionaries(
        st.text(max_size=8),
        st.booleans(),
        max_size=6,
    ),
)
def test_dict_of_flag_schema_values_decode(value: dict[str, bool]) -> None:
    dict_of(Flag).decode(value)


@given(
    st.one_of(st.text(max_size=20), st.integers(min_value=-(10**6), max_value=10**6)),
)
def test_one_of_text_integer_schema_values_decode(value: str | int) -> None:
    one_of(Text, Integer).decode(value)


@given(st.one_of(st.none(), st.text(max_size=20)))
def test_optional_text_schema_values_decode(value: str | None) -> None:
    optional(Text).decode(value)


@given(
    st.lists(
        st.dictionaries(
            st.text(max_size=6),
            st.integers(min_value=-(10**4), max_value=10**4),
            max_size=4,
        ),
        max_size=5,
    ),
)
def test_nested_list_dict_schema_values_decode(value: list[dict[str, int]]) -> None:
    list_of(dict_of(Integer)).decode(value)


@st.composite
def codec_and_valid_raw(draw: st.DrawFn) -> tuple[Codec[object], RawValue]:
    kind = draw(
        st.sampled_from(
            [
                'text',
                'integer',
                'number',
                'flag',
                'null',
                'nothing',
                'list_int',
                'dict_flag',
                'one_of',
                'optional_text',
            ],
        ),
    )
    if kind in {'text', 'integer', 'number'}:
        return _scalar_codec_and_raw(kind, draw)
    if kind in {'flag', 'null', 'nothing'}:
        return _simple_codec_and_raw(kind, draw)
    return _compound_codec_and_raw(kind, draw)


def _scalar_codec_and_raw(kind: str, draw: st.DrawFn) -> tuple[Codec[object], RawValue]:
    if kind == 'text':
        return Text, draw(st.text(max_size=20))
    if kind == 'integer':
        return Integer, draw(st.integers(min_value=-(10**6), max_value=10**6))
    return Number, draw(st.floats(allow_nan=False, allow_infinity=False, width=32))


def _simple_codec_and_raw(kind: str, draw: st.DrawFn) -> tuple[Codec[object], RawValue]:
    if kind == 'flag':
        return Flag, draw(st.booleans())
    if kind == 'null':
        return Null, None
    return Nothing, None


def _compound_codec_and_raw(kind: str, draw: st.DrawFn) -> tuple[Codec[object], RawValue]:
    if kind == 'list_int':
        return list_of(Integer), draw(
            st.lists(st.integers(min_value=-1000, max_value=1000), max_size=6),
        )
    if kind == 'dict_flag':
        return dict_of(Flag), draw(
            st.dictionaries(st.text(max_size=6), st.booleans(), max_size=4),
        )
    if kind == 'one_of':
        return one_of(Text, Integer), draw(
            st.one_of(st.text(max_size=12), st.integers(min_value=-100, max_value=100)),
        )
    return optional(Text), draw(st.one_of(st.none(), st.text(max_size=12)))


@given(pair=codec_and_valid_raw())
def test_schema_valid_raw_decodes_without_payload_error(
    pair: tuple[Codec[object], RawValue],
) -> None:
    """Commuting diagram: inhabit schema ⇒ decode succeeds (no PayloadError)."""
    codec, raw = pair
    codec.decode(raw)  # must not raise


@dataclass(frozen=True, slots=True)
class _SelBranch:
    label: Label
    payload: Codec[object]
    intent: str = ''


_SEL_ORDER = _SelBranch(Label('Order'), Text)
_SEL_QUIT = _SelBranch(Label('Quit'), Nothing)
_SEL_AMOUNT = _SelBranch(Label('Amount'), Integer)
_SEL_BRANCHES: NonEmptyMap[Label, _SelBranch] = branches_map(
    [_SEL_ORDER, _SEL_QUIT, _SEL_AMOUNT],
)


@st.composite
def valid_alt_envelope(
    draw: st.DrawFn,
) -> tuple[NonEmptyMap[Label, _SelBranch], RawValue, RawValue]:
    """(branches, raw_envelope, raw_payload) valid under selection_codec.schema."""
    which = draw(st.sampled_from(['Order', 'Quit', 'Amount']))
    if which == 'Order':
        raw_payload: RawValue = draw(st.text(max_size=20))
    elif which == 'Quit':
        raw_payload = None
    else:
        raw_payload = draw(st.integers(min_value=-(10**6), max_value=10**6))

    envelope: RawValue = {
        'alt': {'label': which, 'payload': raw_payload},
    }
    return _SEL_BRANCHES, envelope, raw_payload


@given(data=valid_alt_envelope())
def test_selection_codec_schema_valid_decodes(
    data: tuple[NonEmptyMap[Label, _SelBranch], RawValue, RawValue],
) -> None:
    branches, envelope, _raw_payload = data
    selection_codec(branches).decode(envelope)


@given(data=valid_alt_envelope())
def test_chosen_payload_is_branch_codec_decode(
    data: tuple[NonEmptyMap[Label, _SelBranch], RawValue, RawValue],
) -> None:
    """Invariant via the real path: selection_codec.decode, not hand-built Chosen."""
    branches, envelope, raw_payload = data
    chosen = selection_codec(branches).decode(envelope)
    assert chosen.payload == chosen.branch.payload.decode(raw_payload)
    assert chosen.branch is branches[chosen.branch.label]
