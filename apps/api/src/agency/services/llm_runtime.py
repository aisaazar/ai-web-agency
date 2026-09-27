"""Durable LLM invocation boundary for agent steps."""
from __future__ import annotations

import hashlib
import json
import time

from sqlalchemy.orm import Session

from agency.db.models import AgentRun, LLMInvocation
from agency.providers.llm import LLMRequest, LLMResponse
from agency.providers.llm_registry import get_llm_provider
from agency.repositories import ArtifactRepository


class LLMRuntimeError(RuntimeError):
    pass


def _prompt_hash(request: LLMRequest) -> str:
    payload = [
        {"role": message.role, "content": message.content}
        for message in request.messages
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def complete_with_logging(
    session: Session,
    *,
    org_id,
    client_id,
    agent: str,
    request: LLMRequest,
    provider_name: str | None = None,
) -> LLMResponse:
    provider = get_llm_provider(provider_name)
    run = AgentRun(
        org_id=org_id,
        client_id=client_id,
        agent=agent,
        status="running",
    )
    session.add(run)
    session.flush()

    started = time.perf_counter()
    prompt_hash = _prompt_hash(request)
    try:
        response = provider.complete(request)
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        session.add(LLMInvocation(
            org_id=org_id,
            client_id=client_id,
            agent_run_id=run.id,
            provider=provider.name,
            model=request.model or getattr(provider, "default_model", "unknown"),
            prompt_hash=prompt_hash,
            tokens_in=0,
            tokens_out=0,
            cost_micros=0,
            latency_ms=latency_ms,
            status="failed",
        ))
        run.status = "failed"
        run.error = str(exc)[:2000]
        session.flush()
        raise LLMRuntimeError(str(exc)) from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    session.add(LLMInvocation(
        org_id=org_id,
        client_id=client_id,
        agent_run_id=run.id,
        provider=provider.name,
        model=response.model,
        prompt_hash=prompt_hash,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_micros=0,
        latency_ms=latency_ms,
        status="completed",
    ))
    run.status = "completed"
    session.flush()
    return response
