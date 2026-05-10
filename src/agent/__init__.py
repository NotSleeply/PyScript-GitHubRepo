"""Agent layer: LLM-driven repository selection from natural-language prompts.

Optional feature — requires the `anthropic` package and an API key. The
SDK is imported lazily inside src.agent.filter so this layer costs
nothing at import time unless actually used."""

from src.agent.filter import (
    AgentError,
    AgentInvalidResponse,
    AgentKeyMissing,
    AgentSDKMissing,
    DEFAULT_MODEL,
    select_repositories,
)

__all__ = [
    "select_repositories",
    "AgentError",
    "AgentSDKMissing",
    "AgentKeyMissing",
    "AgentInvalidResponse",
    "DEFAULT_MODEL",
]
