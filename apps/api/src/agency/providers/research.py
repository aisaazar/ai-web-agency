"""Research provider contracts and deterministic offline implementation."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Source:
    url: str
    title: str
    excerpt: str


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str
    text: str


class ResearchProvider(Protocol):
    name: str

    def search(self, query: str, *, max_results: int) -> list[Source]: ...
    def fetch(self, url: str) -> FetchedPage: ...


@dataclass(frozen=True)
class MockResearchProvider:
    name: str = "mock"

    def search(self, query: str, *, max_results: int) -> list[Source]:
        return [
            Source(
                url=f"https://research.example/{index}",
                title=f"Mock research result {index}",
                excerpt=f"Offline evidence for query: {query}",
            )
            for index in range(1, max_results + 1)
        ]

    def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(url=url, title="Mock fetched page", text=f"Offline page content for {url}")
