from hypothesis import given
from hypothesis import strategies as st

from agentsparty.kernel.role import Role, role, roles


def test_role_creates_instance() -> None:
    r = role('Alice')
    assert isinstance(r, Role)


def test_role_repr_roundtrip() -> None:
    r = role('Alice')
    assert repr(r) == "Role(name='Alice')"


@given(a=st.text(), b=st.text())
def test_structural_equality_iff_names_equal(a: str, b: str) -> None:
    r1 = role(a)
    r2 = role(b)
    assert (r1 == r2) == (a == b)


@given(a=st.text(), b=st.text())
def test_inequality_iff_names_differ(a: str, b: str) -> None:
    r1 = role(a)
    r2 = role(b)
    assert (r1 != r2) == (a != b)


@given(a=st.text(), b=st.text())
def test_hash_consistent_with_equality(a: str, b: str) -> None:
    r1 = role(a)
    r2 = role(b)
    if r1 == r2:
        assert hash(r1) == hash(r2)


@given(x=st.text(), y=st.text(), z=st.text())
def test_equality_transitive(x: str, y: str, z: str) -> None:
    a, b, c = role(x), role(y), role(z)
    if a == b and b == c:
        assert a == c


@given(x=st.text())
def test_equality_reflexive(x: str) -> None:
    r = role(x)
    same = r
    assert r == same


@given(x=st.text(), y=st.text())
def test_equality_symmetric(x: str, y: str) -> None:
    a, b = role(x), role(y)
    assert (a == b) == (b == a)


@given(name=st.text())
def test_role_name_roundtrip(name: str) -> None:
    assert role(name).name == name


@given(name=st.text())
def test_class_constructor_name_roundtrip(name: str) -> None:
    assert Role(name).name == name


@given(names=st.lists(st.text()))
def test_roles_is_role_lifted_over_tuple(names: list[str]) -> None:
    assert roles(*names) == tuple(role(n) for n in names)


@given(name=st.text())
def test_hashable(name: str) -> None:
    r = role(name)
    assert hash(r) == hash(r)
    _ = {r: 42}
