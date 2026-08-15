"""Human-in-the-loop seam: Editor waits on Approve / Revise from the UI."""

from __future__ import annotations

import asyncio
from typing import TypeVar

import agentsparty as ap
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.participant import Envelope, chosen_branch, says
from agentsparty.protocol import Chosen, Label, RawValue
from agentsparty.protocol.language.core import BranchCodec

B = TypeVar('B', bound=BranchCodec)


class QueueDesk:
    """HumanIo whose ``choose`` waits for a button to ``submit`` a label."""

    def __init__(self) -> None:
        self.seen: list[Envelope] = []
        self._decisions: asyncio.Queue[ap.Choice] = asyncio.Queue()
        self._waiting = asyncio.Event()
        self._offered: tuple[str, ...] = ()

    @property
    def offered(self) -> tuple[str, ...]:
        return self._offered

    @property
    def waiting(self) -> bool:
        return self._waiting.is_set()

    def submit(self, label: str, payload: RawValue = None) -> bool:
        if not self.waiting or label not in self._offered:
            return False
        self._decisions.put_nowait(says(label, payload))
        return True

    async def choose(
        self,
        subject: Role,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        del subject, receiver
        self._offered = tuple(str(label) for label in branches)
        self._waiting.set()
        try:
            choice = await self._decisions.get()
            branch = chosen_branch(branches, choice.label)
            payload = branch.payload.decode(choice.payload)
            return Chosen(branch=branch, payload=payload, raw=choice.payload)
        finally:
            self._waiting.clear()
            self._offered = ()

    async def notify(self, subject: Role, envelope: Envelope) -> None:
        del subject
        self.seen.append(envelope)

    async def recall(self, subject: Role, envelope: Envelope) -> None:
        del subject
        self.seen.append(envelope)

    async def cancel(self, subject: Role, notice: object) -> None:
        del subject, notice
        self._waiting.clear()
        self._offered = ()

    def latest(self, name: str) -> object | None:
        return next(
            (item.payload for item in reversed(self.seen) if str(item.label) == name),
            None,
        )
