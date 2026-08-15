# SqliteJournal (/docs/agentsparty/journal/sqlite/SqliteJournal)

Journal that keeps one row per decision in a ``decisions`` table.

The primary key ``(session, track, step)`` makes a duplicated step on
one track impossible at the storage layer: a second writer on the same
track fails instead of silently interleaving two histories.

## Functions

<PyFunction name={"__init__"} type={"(self, connection, proto, session) -> None"}>

Create the table if missing and adopt *session* on *connection*.

The caller owns the connection: opening, closing and any pragmas
(``journal_mode=WAL`` is a good idea) are outside this journal.

<PySourceCode >

```python
def __init__(
    self,
    connection: sqlite3.Connection,
    proto: SessionType,
    session: SessionId,
) -> None:
    """Create the table if missing and adopt *session* on *connection*.

    The caller owns the connection: opening, closing and any pragmas
    (``journal_mode=WAL`` is a good idea) are outside this journal.

    Args:
        connection: An open SQLite connection owned by the caller.
        proto: The choreography this journal belongs to.
        session: Which recorded session to read and extend.

    Raises:
        JournalError: if rows for *session* were written under another
            protocol.
    """
    self._connection = connection
    self._session = session
    self._digest = digest_of(proto)
    connection.execute(SCHEMA)
    connection.commit()
    self._reject_foreign_protocol()
```

</PySourceCode>

<div >

<PyParameter name={"connection"} type={"sqlite3.Connection"} value={undefined}>

An open SQLite connection owned by the caller.

</PyParameter>
<PyParameter name={"proto"} type={"SessionType"} value={undefined}>

The choreography this journal belongs to.

</PyParameter>
<PyParameter name={"session"} type={"SessionId"} value={undefined}>

Which recorded session to read and extend.

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
    rows = self._connection.execute(
        'SELECT track, step, sender, receiver, label, codec, raw '
        'FROM decisions WHERE session = ? ORDER BY track, step',
        (self._session.value,),
    ).fetchall()
    return Script.of(_decision_of(row) for row in rows)
```

</PySourceCode>

<PyFunctionReturn type={"agentsparty.journal.types.Script"} />

</PyFunction>

<PyFunction name={"append"} type={"(self, decision) -> None"}>

Insert *decision* as one row and commit.

<PySourceCode >

```python
def append(self, decision: Decision) -> None:
    """Insert *decision* as one row and commit.

    Args:
        decision: The alt to record.
    """
    track_text = _track_text(decision.step.track)
    recorded = self._connection.execute(
        'SELECT COUNT(*) FROM decisions WHERE session = ? AND track = ?',
        (self._session.value, track_text),
    ).fetchone()[0]
    track_path = decision.step.track.path
    position = decision.step.position
    next_position = recorded + 1
    pre(
        expr=position == recorded + 1,
        message=f'append must extend track {track_path} step {next_position}, got {position}',
    )
    self._connection.execute(
        'INSERT INTO decisions '
        '(session, protocol, track, step, sender, receiver, label, codec, raw) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            self._session.value,
            self._digest.value,
            track_text,
            decision.step.position,
            decision.sender.name,
            decision.receiver.name,
            str(decision.label),
            decision.codec,
            json.dumps(decision.raw),
        ),
    )
    self._connection.commit()
```

</PySourceCode>

<div >

<PyParameter name={"decision"} type={"Decision"} value={undefined}>

The alt to record.

</PyParameter>

</div>

<PyFunctionReturn type={"None"} />

</PyFunction>
