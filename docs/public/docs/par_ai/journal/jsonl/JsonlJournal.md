# JsonlJournal (/docs/agentsparty/journal/jsonl/JsonlJournal)

Journal stored as one JSON object per line in an append-only file.

## Attributes

<PyAttribute name={"session"} type={"SessionId"} value={null}>

Identity recorded in the journal's header.

</PyAttribute>

## Functions

<PyFunction name={"__init__"} type={"(self, path, proto) -> None"}>

Open, or create, the journal at *path* for *proto*.

This is the parsing boundary: an existing file is read and checked
against the protocol's digest, a missing one gets a fresh header.
Nothing downstream re-checks.

<PySourceCode >

```python
def __init__(self, path: Path, proto: SessionType) -> None:
    """Open, or create, the journal at *path* for *proto*.

    This is the parsing boundary: an existing file is read and checked
    against the protocol's digest, a missing one gets a fresh header.
    Nothing downstream re-checks.

    Args:
        path: The journal file.
        proto: The choreography this journal belongs to.

    Raises:
        JournalError: if the file does not read as a journal, or was
            written under a different protocol.
    """
    self._path = path
    self._digest = digest_of(proto)
    if path.exists():
        session, decisions = _read(path, self._digest)
    else:
        session_id = uuid4().hex[:SESSION_ID_LENGTH]
        session = SessionId(session_id)
        decisions = ()
        _write(path, _header_line(session, self._digest))
    self._session = session
    self._script = Script.of(decisions)
```

</PySourceCode>

<div >

<PyParameter name={"path"} type={"Path"} value={undefined}>

The journal file.

</PyParameter>
<PyParameter name={"proto"} type={"SessionType"} value={undefined}>

The choreography this journal belongs to.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>

<PyFunction name={"script"} type={"(self) -> Script"}>

Everything decided so far, one word per track.

<PySourceCode >

```python
def script(self) -> Script:
    """Everything decided so far, one word per track."""
    return self._script
```

</PySourceCode>

<PyFunctionReturn type={"agentsparty.journal.types.Script"} />

</PyFunction>

<PyFunction name={"append"} type={"(self, decision) -> None"}>

Write *decision* as one line and flush it to disk.

<PySourceCode >

```python
def append(self, decision: Decision) -> None:
    """Write *decision* as one line and flush it to disk.

    Args:
        decision: The alt to record.
    """
    _check_append(self._script, decision)
    _write(self._path, _line(decision))
    # rebuild: free interleaving is fine; Script.of re-groups by track
    self._script = Script.of((*self._script.decisions, decision))
```

</PySourceCode>

<div >

<PyParameter name={"decision"} type={"Decision"} value={undefined}>

The alt to record.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
