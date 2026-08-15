"""LLM-driven participant: fills typed payloads and picks declared branches."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Final, Generic, TypeAlias, TypeVar

from agentsparty._utils.assertions import post, require_nonnegative
from agentsparty.brief import Brief, Transcript
from agentsparty.kernel.errors import PayloadError
from agentsparty.kernel.nonempty import NonEmptyMap
from agentsparty.kernel.role import Role
from agentsparty.llm.types import Effort, LanguageModel, Message, StructuredRequest
from agentsparty.participant import Cancelled, Envelope, Participant
from agentsparty.protocol import EndpointType, SessionType, associate
from agentsparty.protocol.language.core import (
    BranchCodec,
    Chosen,
    Codec,
    Label,
    load_json,
    selection_codec,
)
from agentsparty.tracing import scope, signals

current = scope.current
ModelCorrected = signals.ModelCorrected

T = TypeVar('T')
U = TypeVar('U')
B = TypeVar('B', bound=BranchCodec)


@dataclass(frozen=True, slots=True)
class Repair:
    """How many corrections a model is offered when its answer will not decode.

    A person at a console is already re-prompted on a bad payload
    (``CliHumanIo.choose`` loops until the input parses); this gives a model
    the same courtesy, and nothing more. Repair is invisible to the protocol
    and to the journal: nothing is recorded until an answer decodes, so a
    resumed session never repeats a correction, and a protocol reader cannot
    tell a repaired step from a clean one.

    A failure the protocol *declares* is a reply branch, not a repair.
    """

    attempts: int = 1

    def __post_init__(self) -> None:
        """Reject a negative repair budget.

        Raises:
            ValueError: if :attr:`attempts` is below zero.
        """
        require_nonnegative('repair attempts', self.attempts)


NO_REPAIR: Final = Repair(0)
DEFAULT_REPAIR: Final = Repair(1)


@dataclass(frozen=True, slots=True)
class _Decoded(Generic[U]):
    """A model answer that decoded."""

    value: U


@dataclass(frozen=True, slots=True)
class _Unusable:
    """A model answer that would not decode, and why."""

    error: PayloadError


_Attempt: TypeAlias = _Decoded[U] | _Unusable


def _attempt(codec: Codec[U], text: str) -> _Decoded[U] | _Unusable:
    """Decode *text* under *codec*, reporting failure as a value."""
    try:
        return _Decoded(codec.decode(load_json(text)))
    except PayloadError as exc:
        return _Unusable(exc)


def _correction(text: str, error: PayloadError) -> tuple[Message, Message]:
    """The two messages that tell a model its last answer was unusable."""
    return (
        Message(role='assistant', content=text),
        Message(
            role='user',
            content=(
                f'That answer could not be used: {error}. '
                'Answer again, matching the schema exactly.'
            ),
        ),
    )


def _prompt(
    subject: Role,
    receiver: Role,
    branches: NonEmptyMap[Label, B],
) -> Message:
    """The instruction for one selection.

    It is recomputable from the protocol node, so it is never remembered: if it
    were, a replayed session would have to reconstruct it and the two histories
    would drift apart.

    Args:
        subject: The role that is choosing.
        receiver: The role that will receive the message.
        branches: The labelled alts on offer.
    """
    lines = '\n'.join(_offered(branch) for branch in branches.values())
    return Message(
        role='user',
        content=(
            f'You are role {subject.name}. Send exactly one message '
            f'to {receiver.name}.\nBranches:\n{lines}'
        ),
    )


def _offered(branch: BranchCodec) -> str:
    """One branch as the model is told about it: label, and why it exists."""
    if not branch.intent:
        return f'- {branch.label}'
    return f'- {branch.label}: {branch.intent}'


class Agent(Generic[T]):
    """An LLM-driven participant for one role.

    The model never routes the workflow: it only fills a typed payload
    (:meth:`run`) or picks a declared branch (:meth:`select`).

    Memory is a :class:`~agentsparty.brief.Brief` — a pure fold over envelopes the
    agent sent or received. A successful :meth:`select` remembers the alt
    exactly as :meth:`recall` would on a replay, so a resumed session shows the
    model the same conversation the recording session did.
    """

    def __init__(
        self,
        model: LanguageModel,
        role: Role,
        instructions: str,
        proto: SessionType,
        effort: Effort = 'low',
        brief: Brief | None = None,
        repair: Repair = DEFAULT_REPAIR,
        declares: EndpointType | None = None,
    ) -> None:
        """Bind *model* to *role* under *proto*.

        Args:
            model: The language model that fills payloads and picks branches.
            role: The role this agent plays in the protocol.
            instructions: System prompt describing how the agent must behave.
            proto: The choreography; projected locally on construction.
            effort: Reasoning effort passed to the model on every call.
            brief: Initial memory; defaults to an empty
                :class:`~agentsparty.brief.Transcript` for *role*.
            repair: How many corrections the model is offered when an answer
                will not decode. Defaults to one correction.
            declares: An optional endpoint contract; defaults to the projection.

        Raises:
            ConformanceError: if *declares* is not a subtype of the projection.
        """
        self.model = model
        self.role = role
        self.instructions = instructions
        self.effort: Effort = effort
        self.repair = repair

        self.endpoint_contract: EndpointType = associate(declares, proto, role)
        self._initial: Brief = Transcript(role)
        if brief is not None:
            self._initial = brief
        self._brief: Brief = self._initial

    @classmethod
    def at(
        cls,
        model: LanguageModel,
        role: Role,
        instructions: str,
        endpoint: EndpointType,
        effort: Effort = 'low',
        brief: Brief | None = None,
        repair: Repair = DEFAULT_REPAIR,
    ) -> Agent[T]:
        """Bind *model* to *role* under a ready *endpoint* (cast entry).

        Args:
            model: The language model that fills payloads and picks branches.
            role: The role this agent plays.
            instructions: System prompt describing how the agent must behave.
            endpoint: The projected endpoint for *role* (already associated).
            effort: Reasoning effort passed to the model on every call.
            brief: Initial memory; defaults to an empty transcript for *role*.
            repair: How many corrections the model is offered on a bad answer.
        """
        agent: Agent[T] = object.__new__(cls)
        agent.model = model
        agent.role = role
        agent.instructions = instructions
        agent.effort = effort
        agent.repair = repair
        agent.endpoint_contract = endpoint
        agent._initial = Transcript(role) if brief is None else brief
        agent._brief = agent._initial
        return agent

    @property
    def messages(self) -> list[Message]:
        """A copy of the conversation the model would be shown next."""
        return list(self._brief.messages())

    def clear(self) -> None:
        """Reset the agent's memory to the brief it was constructed with."""
        self._brief = self._initial

    async def cancel(self, notice: Cancelled) -> None:
        """Forget the session: memory returns to the brief the agent started with.

        Args:
            notice: Why the session was rolled up.
        """
        self.clear()
        post(
            expr=self._brief == self._initial,
            message='a cancelled agent must hold the brief it was constructed with',
        )

    async def select(
        self,
        receiver: Role,
        branches: NonEmptyMap[Label, B],
    ) -> Chosen[B]:
        """Have the model pick one branch and a matching payload for *receiver*.

        The selection prompt is recomputed from the protocol node and is never
        remembered. The chosen envelope is remembered in the same rendered form
        that :meth:`recall` would use on a replay.

        Args:
            receiver: The role that will receive the chosen message.
            branches: The labelled alts offered to the model.

        Returns:
            The chosen branch together with its decoded payload.
        """
        offered = branches
        # build the request from memory plus a prompt that is *not* remembered:
        codec = selection_codec(offered)
        conversation = (*self._brief.messages(), _prompt(self.role, receiver, offered))
        chosen = await self._author(
            'agent_alt',
            codec,
            conversation,
            self.repair.attempts,
        )
        # remember the alt exactly as `recall` would on a replay:
        self._brief = self._brief.remember(
            Envelope(self.role, receiver, chosen.branch.label, chosen.payload),
        )
        return chosen

    async def offer(self, envelope: Envelope) -> None:
        """Record *envelope* as an incoming message in the conversation.

        Same transition as :meth:`recall`: both fold *envelope* into the brief,
        which is what makes a resumed session faithful.

        Args:
            envelope: The protocol message being delivered.
        """
        self._brief = self._brief.remember(envelope)

    async def recall(self, envelope: Envelope) -> None:
        """Record *envelope* as a message this agent sent earlier.

        Same transition as :meth:`offer`: both fold *envelope* into the brief,
        which is what makes a resumed session faithful.

        Args:
            envelope: The protocol message this agent sent earlier.
        """
        self._brief = self._brief.remember(envelope)

    async def run(self, prompt: str, output_type: Codec[T]) -> T:
        """Ask the model a free-form *prompt* and decode its answer.

        A free-form request is not a protocol act, so it leaves no brief
        memory and cannot change what the next :meth:`select` shows the model.

        Args:
            prompt: The user message sent to the model.
            output_type: Codec describing the expected JSON payload.

        Returns:
            The decoded payload.
        """
        conversation = (*self._brief.messages(), Message(role='user', content=prompt))
        return await self._author(
            'agent_output',
            output_type,
            conversation,
            self.repair.attempts,
        )

    async def _complete(
        self,
        schema_name: str,
        schema: dict[str, object],
        conversation: tuple[Message, ...],
    ) -> str:
        """Ask the model once; return its raw text without decoding.

        The rest of the answer — who produced it and what it cost — is a
        receipt, not a protocol value: it reaches the session through the
        tracer (see :func:`agentsparty.tracing.model.traced`) and never through the
        journal.
        """
        answer = await self.model.complete(
            StructuredRequest(
                instructions=self.instructions,
                messages=conversation,
                schema_name=schema_name,
                schema=schema,
                effort=self.effort,
            ),
        )
        return answer.text

    async def _author(
        self,
        schema_name: str,
        codec: Codec[U],
        conversation: tuple[Message, ...],
        attempts: int,
    ) -> U:
        """The first answer that decodes, correcting the model *attempts* times.

        Recursion depth is ``attempts + 1`` and *attempts* is validated as
        non-negative at construction, so unbounded recursion cannot arise.

        Args:
            schema_name: The name the request carries for the schema.
            codec: The codec the answer must decode under.
            conversation: The messages sent with this request.
            attempts: Corrections still available.

        Returns:
            The decoded answer.

        Raises:
            PayloadError: if the budget runs out before an answer decodes.
        """
        text = await self._complete(schema_name, dict(codec.schema), conversation)
        match _attempt(codec, text):
            case _Decoded(value=value):
                return value
            case _Unusable(error=error) if attempts > 0:
                current().record(ModelCorrected(str(error)))
                return await self._author(
                    schema_name,
                    codec,
                    (*conversation, *_correction(text, error)),
                    attempts - 1,
                )
            case _Unusable(error=error):
                raise error


def _bind_agent(
    model: LanguageModel,
    instructions: str,
    effort: Effort,
    brief: Brief | None,
    repair: Repair,
    role: Role,
    endpoint: EndpointType,
) -> Participant:
    return Agent.at(
        model,
        role,
        instructions,
        endpoint,
        effort=effort,
        brief=brief,
        repair=repair,
    )


def agent(
    model: LanguageModel,
    instructions: str,
    *,
    effort: Effort = 'low',
    brief: Brief | None = None,
    repair: Repair = DEFAULT_REPAIR,
) -> Callable[[Role, EndpointType], Participant]:
    """Casting factory: bind *model* and *instructions* when a role is played.

    Returns a ``(role, endpoint) -> Agent`` for :meth:`~agentsparty.runtime.Cast.play`.

    Args:
        model: The language model that fills payloads and picks branches.
        instructions: System prompt describing how the agent must behave.
        effort: Reasoning effort passed to the model on every call.
        brief: Initial memory; defaults to an empty transcript for the role.
        repair: How many corrections the model is offered on a bad answer.
    """
    return partial(_bind_agent, model, instructions, effort, brief, repair)


__all__ = ['DEFAULT_REPAIR', 'NO_REPAIR', 'Agent', 'Repair', 'agent']
