"""Durable LLM invocation boundary for agent steps."""
from __future__ import annotations

import hashlib
import json
import time

from sqlalchemy.orm import Session

from agency.db.models import AgentRun, LLMInvocation
from agency.providers.llm import LLMRequest, LLMResponse
from agency.providers.llm_registry import get_llm_provider
from agency.services.llm_budget_service import (
    LLMBudgetExceeded,
    LLMPricingMissing,
    enforce_budget,
    record_cost,
)


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
    model = request.model or getattr(provider, "default_model", getattr(provider, "model", "unknown"))
    prompt_tokens = sum(len(message.content.split()) for message in request.messages)
    run = AgentRun(
        org_id=org_id,
        client_id=client_id,
        agent=agent,
        status="running",
    )
    session.add(run)
    session.flush()

    try:
        enforce_budget(
            session,
            org_id=org_id,
            client_id=client_id,
            provider=provider.name,
            model=model,
            prompt_tokens=prompt_tokens,
            max_output_tokens=request.max_tokens,
        )
    except (LLMBudgetExceeded, LLMPricingMissing) as exc:
        session.add(LLMInvocation(
            org_id=org_id,
            client_id=client_id,
            agent_run_id=run.id,
            provider=provider.name,
            model=model,
            prompt_hash=_prompt_hash(request),
            tokens_in=prompt_tokens,
            tokens_out=0,
            cost_micros=0,
            latency_ms=0,
            status="budget_blocked" if isinstance(exc, LLMBudgetExceeded) else "pricing_error",
        ))
        run.status = "failed"
        run.error = str(exc)[:2000]
        session.flush()
        raise LLMRuntimeError(str(exc)) from exc

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
            model=model,
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
    invocation = LLMInvocation(
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
    )
    session.add(invocation)
    session.flush()
    record_cost(
        session,
        invocation=invocation,
        provider=provider.name,
        model=response.model,
    )
    run.status = "completed"
    session.flush()
    return response
