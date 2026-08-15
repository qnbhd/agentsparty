"""Contracts for the neutral protocol graph used by documentation diagrams."""

from agentsparty.kernel.role import roles
from agentsparty.protocol import Text, alt, case, msg, project, to_graph


def test_blind_alt_has_exactly_one_gap_for_the_observer() -> None:
    A, B, C = roles('A', 'B', 'C')
    protocol = alt[A, B](
        case('Yes') >> msg[A, C]('Y', Text),
        case('No') >> msg[C, A]('N', Text),
    ).close()

    graph = to_graph(protocol, role=C)

    assert sum(edge['kind'] == 'gap' for edge in graph['edges']) == 1
    assert next(edge for edge in graph['edges'] if edge['kind'] == 'gap')['role'] == 'C'


def test_observable_alt_has_no_gap() -> None:
    A, B, C = roles('A', 'B', 'C')
    protocol = alt[A, B](
        case('Yes') >> msg[A, C]('Yes', Text) >> msg[A, C]('Y', Text),
        case('No') >> msg[A, C]('No', Text) >> msg[C, A]('N', Text),
    ).close()

    graph = to_graph(protocol, role=C)

    assert not [edge for edge in graph['edges'] if edge['kind'] == 'gap']


def test_endpoint_graph_requires_and_keeps_the_subject_role() -> None:
    A, B = roles('A', 'B')
    endpoint = project(msg[A, B]('Draft', Text).close(), B)

    graph = to_graph(endpoint, role=B)

    assert graph['roles'] == ['B']
    assert graph['nodes'][0]['kind'] == 'alt'
