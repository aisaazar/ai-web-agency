"""Tavily-backed implementation of the frozen research provider contract."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agency.providers.research import FetchedPage, Source
from agency.services.url_security import UnsafeFetchURL, validate_fetch_url


class TavilyProviderError(RuntimeError):
    """Raised when Tavily cannot return a valid provider response."""


@dataclass(frozen=True)
class TavilyResearchProvider:
    name: str = "tavily"
    search_endpoint: str = "https://api.tavily.com/search"
    extract_endpoint: str = "https://api.tavily.com/extract"
    timeout_seconds: float = 30.0

    def _api_key(self) -> str:
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            raise TavilyProviderError("TAVILY_API_KEY is not configured")
        return key

    def _post(self, endpoint: str, payload: dict) -> dict:
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise TavilyProviderError(f"Tavily HTTP {exc.code} from {endpoint}") from exc
        except URLError as exc:
            raise TavilyProviderError(f"Tavily request failed for {endpoint}: {exc.reason}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TavilyProviderError(f"Tavily returned invalid JSON from {endpoint}") from exc
        if not isinstance(data, dict):
            raise TavilyProviderError(f"Tavily response from {endpoint} is not an object")
        return data

    def search(self, query: str, *, max_results: int) -> list[Source]:
        if not query.strip():
            raise TavilyProviderError("research query must not be empty")
        if max_results < 1:
            raise TavilyProviderError("max_results must be at least 1")
        data = self._post(self.search_endpoint, {
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        })
        results = data.get("results")
        if not isinstance(results, list):
            raise TavilyProviderError("Tavily search response has no results list")
        sources = []
        for item in results[:max_results]:
            if not isinstance(item, dict):
                raise TavilyProviderError("Tavily search result is not an object")
            url = item.get("url")
            title = item.get("title")
            excerpt = item.get("content")
            if not all(isinstance(value, str) and value.strip() for value in (url, title, excerpt)):
                raise TavilyProviderError("Tavily search result is missing url/title/content")
            sources.append(Source(url=url, title=title, excerpt=excerpt))
        return sources

    def fetch(self, url: str) -> FetchedPage:
        try:
            validate_fetch_url(url)
        except UnsafeFetchURL as exc:
            raise TavilyProviderError(str(exc)) from exc
        data = self._post(self.extract_endpoint, {
            "urls": [url],
            "include_images": False,
        })
        results = data.get("results")
        if not isinstance(results, list) or not results:
            raise TavilyProviderError("Tavily extract response has no results")
        item = results[0]
        if not isinstance(item, dict):
            raise TavilyProviderError("Tavily extract result is not an object")
        extracted_url = item.get("url") or url
        text = item.get("raw_content") or item.get("content")
        if not isinstance(extracted_url, str) or not extracted_url.strip():
            raise TavilyProviderError("Tavily extract result is missing url")
        if not isinstance(text, str) or not text.strip():
            raise TavilyProviderError("Tavily extract result is missing content")
        return FetchedPage(url=extracted_url, title=url, text=text)
