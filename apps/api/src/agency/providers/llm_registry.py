"""LLM provider registry."""
from collections.abc import Callable

from agency.providers.llm import (
    LLMProvider,
    LocalOpenAICompatibleProvider,
    MockLLMProvider,
)

_LLM_REGISTRY: dict[str, Callable[[], LLMProvider]] = {
    "mock": MockLLMProvider,
    "local": LocalOpenAICompatibleProvider,
}


def get_llm_provider(name: str | None = None) -> LLMProvider:
    provider_name = name or __import__("os").getenv("AGENCY_LLM_PROVIDER", "mock")
    try:
        return _LLM_REGISTRY[provider_name]()
    except KeyError as exc:
        raise NotImplementedError(
            f"LLM provider '{provider_name}' is not registered"
        ) from exc
