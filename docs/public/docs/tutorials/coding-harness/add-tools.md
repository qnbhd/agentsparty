# Add tools (/docs/tutorials/coding-harness/add-tools)

The protocol describes the conversation. This page implements `Workspace`, the
participant that performs filesystem operations for the planner and coder.

Continue appending each block to `coding_agent.py`.

<Steps>

<Step>
### Confine paths to the workspace

All filesystem handlers share one resolver. It combines the workspace root with
a relative path, resolves symbolic links and `..`, and accepts the result only
when it remains beneath the resolved root.

```python compile
def _inside(root: Path, rel: str) -> Path | None:
    candidate = (root / (rel or '.')).resolve()
    if not candidate.is_relative_to(root.resolve()):
        return None
    return candidate
```

`RelPath` already parses planner requests. `_inside` enforces the filesystem
boundary for every operation, including the `path` field inside a `Write`
record. Keeping the check beside path resolution also covers symbolic links.
</Step>

<Step>
### Implement the workspace replies

A service handler receives a decoded payload and returns `ap.reply(...)` with
the response label and payload expected by the protocol.

```python compile
async def _ack(_empty: None) -> ap.Choice:
    return ap.reply(Noted, None)


def _list_dir(root: Path, rel: str) -> ap.Choice:
    path = _inside(root, rel)
    if path is None or not path.is_dir():
        return ap.reply(Listing, [])
    names = sorted(
        child.relative_to(root).as_posix() for child in path.iterdir()
    )
    return ap.reply(Listing, names)


def _read_file(root: Path, rel: str) -> ap.Choice:
    path = _inside(root, rel)
    if path is None or not path.is_file():
        return ap.reply(Source, f'missing: {rel}')
    return ap.reply(Source, path.read_text(encoding='utf-8'))


def _write_file(root: Path, payload: dict[str, str]) -> ap.Choice:
    path = _inside(root, payload['path'])
    if path is None:
        return ap.reply(Saved, 'refused: path escapes the workspace')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload['content'], encoding='utf-8')
    return ap.reply(Saved, path.relative_to(root).as_posix())
```

Invalid reads produce ordinary protocol replies because a missing path is an
expected workspace outcome. A refused write also returns through `Saved`, which
keeps the session synchronized and gives the coder a concrete result to handle.

Bind these operations to their request labels. The nested functions capture
`root`, so every tool in the service operates on the same directory.

```python compile
def workspace_tools(root: Path) -> list[Any]:
    async def list_dir(rel: str) -> ap.Choice:
        return _list_dir(root, rel)

    async def read_file(rel: str) -> ap.Choice:
        return _read_file(root, rel)

    async def write(payload: dict[str, str]) -> ap.Choice:
        return _write_file(root, payload)

    return [
        ap.tool_for(List, list_dir),
        ap.tool_for(Read, read_file),
        ap.tool_for(Ready, _ack),
        ap.tool_for(Write, write),
        ap.tool_for(Done, _ack),
        ap.tool_for(Idle, _ack),
    ]
```

`ap.service` will dispatch incoming workspace messages through this table. Its
available handlers cover every branch projected for `Workspace`.
</Step>

</Steps>

Continue with [bind the roles and run](/docs/tutorials/coding-harness/bind-and-run) to add the
model-backed participants, terminal client, and runtime.

