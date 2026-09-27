"""Preflight LLM spend accounting and hard budget checks."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agency.db.llm_budget_models import ClientLLMBudget
from agency.db.models import Client, LLMInvocation, Org


@dataclass(frozen=True)
class LLMPricing:
    input_micros_per_1k: int
    output_micros_per_1k: int


PRICING: dict[tuple[str, str], LLMPricing] = {
    ("mock", "*"): LLMPricing(0, 0),
    ("local", "*"): LLMPricing(0, 0),
}


class LLMBudgetExceeded(RuntimeError):
    pass


class LLMPricingMissing(RuntimeError):
    pass


def register_pricing(provider: str, model: str, pricing: LLMPricing) -> None:
    if pricing.input_micros_per_1k < 0 or pricing.output_micros_per_1k < 0:
        raise ValueError("LLM pricing cannot be negative")
    PRICING[(provider, model)] = pricing


def _pricing(provider: str, model: str) -> LLMPricing:
    pricing = PRICING.get((provider, model)) or PRICING.get((provider, "*"))
    if pricing is None:
        raise LLMPricingMissing(
            f"no pricing configured for provider={provider!r}, model={model!r}"
        )
    return pricing


def _cost(tokens: int, micros_per_1k: int) -> int:
    if tokens < 0:
        raise ValueError("LLM token counts cannot be negative")
    if tokens == 0 or micros_per_1k == 0:
        return 0
    return ceil(tokens * micros_per_1k / 1000)


def estimate_cost_micros(*, provider: str, model: str, tokens_in: int, tokens_out: int) -> int:
    pricing = _pricing(provider, model)
    return _cost(tokens_in, pricing.input_micros_per_1k) + _cost(tokens_out, pricing.output_micros_per_1k)


def _spent(session: Session, *, org_id, client_id=None) -> int:
    query = select(func.coalesce(func.sum(LLMInvocation.cost_micros), 0)).where(
        LLMInvocation.org_id == org_id,
        LLMInvocation.status == "completed",
    )
    if client_id is not None:
        query = query.where(LLMInvocation.client_id == client_id)
    return int(session.scalar(query) or 0)


def _client_cap(session: Session, *, org_id, client_id) -> int:
    row = session.scalar(select(ClientLLMBudget).where(
        ClientLLMBudget.org_id == org_id,
        ClientLLMBudget.client_id == client_id,
    ))
    if row is not None:
        return int(row.budget_micros)
    org = session.get(Org, org_id)
    return int(org.llm_budget_micros) if org is not None else 0


def enforce_budget(
    session: Session,
    *,
    org_id,
    client_id,
    provider: str,
    model: str,
    prompt_tokens: int,
    max_output_tokens: int,
) -> None:
    estimated = estimate_cost_micros(
        provider=provider,
        model=model,
        tokens_in=prompt_tokens,
        tokens_out=max_output_tokens,
    )
    if estimated == 0:
        return

    org = session.get(Org, org_id)
    if org is None:
        raise LLMBudgetExceeded("organization not found")
    org_cap = int(org.llm_budget_micros)
    client_cap = _client_cap(session, org_id=org_id, client_id=client_id)
    org_spent = _spent(session, org_id=org_id)
    client_spent = _spent(session, org_id=org_id, client_id=client_id)

    if org_cap <= 0 or org_spent + estimated > org_cap:
        raise LLMBudgetExceeded("organization LLM budget exceeded")
    if client_cap <= 0 or client_spent + estimated > client_cap:
        raise LLMBudgetExceeded("client LLM budget exceeded")


def record_cost(
    session: Session,
    *,
    invocation: LLMInvocation,
    provider: str,
    model: str,
) -> int:
    cost = estimate_cost_micros(
        provider=provider,
        model=model,
        tokens_in=invocation.tokens_in,
        tokens_out=invocation.tokens_out,
    )
    invocation.cost_micros = cost
    return cost
