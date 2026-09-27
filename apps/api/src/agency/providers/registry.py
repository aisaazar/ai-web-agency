"""Research provider registry; services depend on this seam."""
from collections.abc import Callable

from agency.providers.research import MockResearchProvider, ResearchProvider
from agency.providers.research_tavily import TavilyResearchProvider


_RESEARCH_REGISTRY: dict[str, Callable[[], ResearchProvider]] = {
    "mock": MockResearchProvider,
    "tavily": TavilyResearchProvider,
}


def get_research_provider(name: str = "mock") -> ResearchProvider:
    try:
        return _RESEARCH_REGISTRY[name]()
    except KeyError as exc:
        raise NotImplementedError(f"Research provider '{name}' is not registered") from exc
