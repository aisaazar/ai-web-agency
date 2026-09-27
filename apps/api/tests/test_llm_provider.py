import json

import pytest

from agency.providers.llm import (
    LLMMessage,
    LLMProviderError,
    LLMRequest,
    LocalOpenAICompatibleProvider,
    MockLLMProvider,
)
from agency.providers.llm_registry import get_llm_provider


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def _request():
    return LLMRequest(
        messages=(LLMMessage("user", "Write one short sentence."),),
        temperature=0.1,
        max_tokens=20,
    )


def test_mock_llm_is_deterministic():
    response = MockLLMProvider().complete(_request())
    assert response.model == "mock-model"
    assert json.loads(response.content)["echo"] == "Write one short sentence."


def test_local_llm_maps_openai_compatible_response(monkeypatch):
    calls = []
    monkeypatch.setenv("AGENCY_LOCAL_LLM_MODEL", "qwen3:0.6b")
    def fake_urlopen(request, timeout):
        calls.append((request.full_url, json.loads(request.data), request.headers))
        return _Response({
            "model": "qwen3:0.6b",
            "choices": [{"message": {"content": "Hello from local model."}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 4},
        })

    monkeypatch.setattr("agency.providers.llm.urlopen", fake_urlopen)
    response = LocalOpenAICompatibleProvider().complete(_request())

    assert response.content == "Hello from local model."
    assert response.tokens_in == 7
    assert response.tokens_out == 4
    assert calls[0][0].endswith("/v1/chat/completions")


def test_local_llm_rejects_malformed_response(monkeypatch):
    monkeypatch.setattr(
        "agency.providers.llm.urlopen",
        lambda request, timeout: _Response({"choices": []}),
    )
    with pytest.raises(LLMProviderError, match="missing choices"):
        LocalOpenAICompatibleProvider().complete(_request())


def test_llm_registry_exposes_mock_and_local(monkeypatch):
    monkeypatch.setenv("AGENCY_LLM_PROVIDER", "mock")
    assert get_llm_provider().name == "mock"
    assert get_llm_provider("local").name == "local"
