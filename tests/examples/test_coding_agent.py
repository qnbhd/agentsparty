"""The coding-agent protocol is the control: plan cannot write; review is one-shot."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from agentsparty.protocol import project, project_all
from agentsparty.protocol.language.endpoint import (
    EndpointBranch,
    EndpointEnd,
    EndpointRec,
    EndpointSelect,
    EndpointType,
    EndpointVar,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'examples' / 'coding_agent.py'


def _load():
    spec = importlib.util.spec_from_file_location('agentsparty_examples_coding_agent', EXAMPLE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _from_branches(branches) -> list:
    return [item for branch in branches.values() for item in _selects(branch.continuation)]


def _selects(node: EndpointType):
    match node:
        case EndpointEnd() | EndpointVar():
            return
        case EndpointRec(body=body):
            yield from _selects(body)
        case EndpointBranch(branches=branches):
            yield from _from_branches(branches)
        case EndpointSelect(receiver=receiver, branches=branches):
            yield receiver, branches
            yield from _from_branches(branches)


def test_example_projects() -> None:
    module = _load()
    project_all(module.protocol)


def test_planner_workspace_offers_only_reads() -> None:
    module = _load()
    offered: set = set()
    for receiver, branches in _selects(project(module.protocol, module.Planner)):
        if receiver == module.Workspace:
            offered.update(branches)
    assert offered == {module.List.label, module.Read.label, module.Ready.label}
    assert module.Write.label not in offered
    assert module.Idle.label not in offered


def test_reviewer_selects_once_then_ends() -> None:
    module = _load()
    selects = list(_selects(project(module.protocol, module.Reviewer)))
    assert len(selects) == 1
    receiver, branches = selects[0]
    assert receiver == module.Coder
    assert set(branches) == {module.Ship.label, module.Fix.label}
    for branch in branches.values():
        assert isinstance(branch.continuation, EndpointEnd)


def test_write_refuses_path_escape(tmp_path: Path) -> None:
    module = _load()
    choice = module._write_file(tmp_path, {'path': '../secret.py', 'content': 'no'})
    assert choice.label == module.Saved.label
    assert 'refused' in choice.payload
    assert not (tmp_path.parent / 'secret.py').exists()


def test_build_cast_binds_the_interactive_client(tmp_path: Path) -> None:
    module = _load()
    client_io = module.ap.CliHumanIo()
    cast = module.build_cast(tmp_path, client_io=client_io, model=object())

    client = cast._players[0]
    assert isinstance(client, module.ap.Human)
    assert client._io is client_io
