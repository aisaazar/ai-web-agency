"""Typed LLM provider contract with deterministic mock and local OpenAI-compatible transport."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[LLMMessage, ...]
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1200


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


class LLMProvider(Protocol):
    name: str

    def complete(self, request: LLMRequest) -> LLMResponse: ...


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot return a valid response."""


@dataclass(frozen=True)
class MockLLMProvider:
    name: str = "mock"
    model: str = "mock-model"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not request.messages:
            raise LLMProviderError("LLM request requires at least one message")
        prompt = request.messages[-1].content.strip()
        if not prompt:
            raise LLMProviderError("LLM message content must not be empty")
        return LLMResponse(
            content=json.dumps(
                {"mock": True, "echo": prompt},
                ensure_ascii=False,
            ),
            model=request.model or self.model,
            tokens_in=sum(len(m.content.split()) for m in request.messages),
            tokens_out=len(prompt.split()),
        )


@dataclass(frozen=True)
class LocalOpenAICompatibleProvider:
    name: str = "local"
    base_url: str = ""
    default_model: str = ""
    api_key: str | None = None
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not self.base_url:
            object.__setattr__(
                self,
                "base_url",
                os.getenv("AGENCY_LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
            )
        if not self.default_model:
            object.__setattr__(
                self,
                "default_model",
                os.getenv("AGENCY_LOCAL_LLM_MODEL", "qwen3:0.6b"),
            )
        if self.api_key is None:
            object.__setattr__(self, "api_key", os.getenv("AGENCY_LOCAL_LLM_API_KEY"))

    def complete(self, request: LLMRequest) -> LLMResponse:
        if not request.messages:
            raise LLMProviderError("LLM request requires at least one message")
        if not 0 <= request.temperature <= 2:
            raise LLMProviderError("temperature must be between 0 and 2")
        if request.max_tokens < 1:
            raise LLMProviderError("max_tokens must be at least 1")

        reasoning_effort = os.getenv("AGENCY_LOCAL_LLM_REASONING_EFFORT", "none").strip().lower()
        if reasoning_effort not in {"high", "medium", "low", "max", "none"}:
            raise LLMProviderError("AGENCY_LOCAL_LLM_REASONING_EFFORT must be high, medium, low, max, or none")

        payload = {
            "model": request.model or self.default_model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "reasoning_effort": reasoning_effort,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            raise LLMProviderError(f"local LLM HTTP {exc.code}") from exc
        except URLError as exc:
            raise LLMProviderError(f"local LLM request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LLMProviderError("local LLM request timed out") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMProviderError("local LLM returned invalid JSON") from exc

        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = message["content"]
            if not isinstance(content, str) or not content.strip():
                raise TypeError
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("local LLM response is missing choices[0].message.content") from exc

        usage = data.get("usage") or {}
        return LLMResponse(
            content=content,
            model=str(data.get("model") or request.model or self.default_model),
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
        )
