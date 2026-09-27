import json

import pytest

from agency.providers.registry import get_research_provider
from agency.providers.research_tavily import TavilyProviderError, TavilyResearchProvider


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def test_tavily_search_maps_results(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.get_header("Authorization"), timeout, json.loads(request.data)))
        return _Response({
            "results": [{"url": "https://example.com", "title": "Example", "content": "Evidence"}],
        })

    monkeypatch.setattr(
        "agency.providers.research_tavily.urlopen",
        fake_urlopen,
    )
    provider = TavilyResearchProvider()
    sources = provider.search("dentist Germany", max_results=3)

    assert sources[0].url == "https://example.com"
    assert sources[0].title == "Example"
    assert sources[0].excerpt == "Evidence"
    assert calls[0][0] == "https://api.tavily.com/search"
    assert calls[0][1] == "Bearer test-key"
    assert calls[0][3]["max_results"] == 3


def test_tavily_fetch_maps_extracted_content(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    monkeypatch.setattr(
        "agency.providers.research_tavily.urlopen",
        lambda request, timeout: _Response({
            "results": [{
                "url": "https://example.com",
                "raw_content": "Extracted page text",
            }],
        }),
    )
    page = TavilyResearchProvider().fetch("https://example.com")

    assert page.url == "https://example.com"
    assert page.text == "Extracted page text"


def test_tavily_missing_key_fails_without_network(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    provider = TavilyResearchProvider()

    with pytest.raises(TavilyProviderError, match="TAVILY_API_KEY"):
        provider.search("query", max_results=1)


def test_tavily_malformed_response_fails(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(
        "agency.providers.research_tavily.urlopen",
        lambda request, timeout: _Response({"unexpected": []}),
    )

    with pytest.raises(TavilyProviderError, match="no results list"):
        TavilyResearchProvider().search("query", max_results=1)


def test_registry_exposes_tavily(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    provider = get_research_provider("tavily")
    assert provider.name == "tavily"
