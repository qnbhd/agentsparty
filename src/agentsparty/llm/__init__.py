"""The language-model contract, its profiles, and the ways models compose."""

from agentsparty.llm.compose import Fallback, Metered, Retrying, Unavailable, fallback
from agentsparty.llm.profile import EVERY_EFFORT, NO_REASONING, Profile, Profiled
from agentsparty.llm.scripted import ScriptedLanguageModel
from agentsparty.llm.types import (
    EFFORTS,
    LEAST_EFFORT,
    NO_USAGE,
    Answer,
    ChatRole,
    Effort,
    LanguageModel,
    Message,
    ModelId,
    StructuredRequest,
    Usage,
)

# Sleep is a TypeAlias (Callable) — re-exporting it would put a bare Callable
# into __all__, and docs-coverage would demand a docstring on that class.
# Import it from agentsparty.llm.compose when typing a custom wait.

# Provider backends (e.g. agentsparty.llm.openai) are deliberately not re-exported:
# importing one here would drag its provider SDK into every agentsparty import.
# ScriptedLanguageModel is provider-free and is the public offline test double.
__all__ = [
    'EFFORTS',
    'EVERY_EFFORT',
    'LEAST_EFFORT',
    'NO_REASONING',
    'NO_USAGE',
    'Answer',
    'ChatRole',
    'Effort',
    'Fallback',
    'LanguageModel',
    'Message',
    'Metered',
    'ModelId',
    'Profile',
    'Profiled',
    'Retrying',
    'ScriptedLanguageModel',
    'StructuredRequest',
    'Unavailable',
    'Usage',
    'fallback',
]
