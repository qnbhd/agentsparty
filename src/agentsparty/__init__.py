"""Declarative multiparty session protocols for AI agents.

The public surface lives in submodules, with the codec vocabulary and other
commonly used names re-exported here. The protocol DSL remains an explicit
submodule import, except for the codec vocabulary described by ADR 0059:

- ``agentsparty.protocol`` — the protocol DSL, codecs, projection and rendering;
- ``agentsparty.participant`` — the participant contract (``select`` / ``offer``);
- ``agentsparty.agent``, ``agentsparty.human``, ``agentsparty.machine``, ``agentsparty.toolbox``
  — the four kinds of participant;
- ``agentsparty.runtime`` — binds roles to participants and executes a protocol;
- ``agentsparty.kernel.role``, ``agentsparty.brief``, ``agentsparty.kernel.budget``,
  ``agentsparty.kernel.console``,
  ``agentsparty.kernel.errors`` — the vocabulary they share;
- ``agentsparty.llm`` — the language-model contract;
- ``agentsparty.journal`` — durable decisions;
- ``agentsparty.tracing`` — observability.
- ``agentsparty.debug`` — human-readable reports of protocols and runs.

"""

from typing import TYPE_CHECKING

from agentsparty.agent import Agent, Repair, agent
from agentsparty.brief import Recent
from agentsparty.choreography import Chor, choreography
from agentsparty.human import CliHumanIo, Human, ScriptedHumanIo, human, script
from agentsparty.journal import JsonlJournal, MemoryJournal
from agentsparty.kernel.budget import Allowance
from agentsparty.kernel.errors import (
    CompositionError,
    ConformanceError,
    ProjectionError,
    RecursionLimitError,
    SelectionError,
    StepLimitError,
    TokenLimitError,
)
from agentsparty.kernel.role import roles
from agentsparty.llm import (
    LanguageModel,
    Message,
    Metered,
    ModelId,
    Retrying,
    ScriptedLanguageModel,
    StructuredRequest,
    Unavailable,
    fallback,
)
from agentsparty.machine import Machine, View
from agentsparty.participant import Choice, Participant, says
from agentsparty.protocol import (
    Codec,
    Flag,
    Integer,
    Nothing,
    Null,
    Number,
    Text,
    json_model,
    record,
)
from agentsparty.runtime import AgentRuntime, Cast
from agentsparty.toolbox import Toolbox, reply, service, tool_for
from agentsparty.tracing import (
    Delivered,
    Event,
    Failed,
    MemoryTracer,
    ModelAnswered,
    ModelCalled,
    ModelCorrected,
    ModelStreamed,
    QueueTracer,
    Recalled,
    Selected,
    SessionFinished,
    SessionStarted,
    StepStarted,
    Unfolded,
    traced,
    watching,
)

__version__ = '0.1.1'

__all__ = [
    'Agent',
    'AgentRuntime',
    'Allowance',
    'Cast',
    'Choice',
    'Chor',
    'CliHumanIo',
    'Codec',
    'CompositionError',
    'ConformanceError',
    'Delivered',
    'Event',
    'Failed',
    'Flag',
    'Human',
    'Integer',
    'JsonlJournal',
    'LanguageModel',
    'Machine',
    'MemoryJournal',
    'MemoryTracer',
    'Message',
    'Metered',
    'ModelAnswered',
    'ModelCalled',
    'ModelCorrected',
    'ModelId',
    'ModelStreamed',
    'Nothing',
    'Null',
    'Number',
    'OpenAIModel',
    'Participant',
    'ProjectionError',
    'QueueTracer',
    'Recalled',
    'Recent',
    'RecursionLimitError',
    'Repair',
    'Retrying',
    'ScriptedHumanIo',
    'ScriptedLanguageModel',
    'Selected',
    'SelectionError',
    'SessionFinished',
    'SessionStarted',
    'StepLimitError',
    'StepStarted',
    'StructuredRequest',
    'Text',
    'TokenLimitError',
    'Toolbox',
    'Unavailable',
    'Unfolded',
    'View',
    '__version__',
    'agent',
    'choreography',
    'fallback',
    'human',
    'json_model',
    'record',
    'reply',
    'roles',
    'says',
    'script',
    'service',
    'tool_for',
    'traced',
    'watching',
]

if TYPE_CHECKING:
    # Type checkers and IDEs see the name; the runtime resolves it on demand.
    from agentsparty.llm.openai import OpenAIModel as OpenAIModel


def __getattr__(name: str) -> object:  # noqa: WPS413
    """Resolve provider backends on first use (PEP 562).

    ``OpenAIModel`` reaches the ``openai`` SDK, which the ``openai`` extra
    installs. Importing it eagerly would make ``import agentsparty`` fail for
    everyone who did not ask for that extra, so the name is bound here
    instead — and only the attribute access, not the import, raises.
    """
    if name == 'OpenAIModel':
        from agentsparty.llm.openai import OpenAIModel

        return OpenAIModel
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
