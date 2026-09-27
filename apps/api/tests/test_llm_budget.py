import anyio
import pytest

from agency.api import create_app
from agency.db.llm_budget_models import ClientLLMBudget
from agency.db.models import Client, LLMInvocation, Org
from agency.db.session import create_all, create_session_factory
from agency.providers.llm import LLMMessage, LLMRequest, LLMResponse
from agency.services.llm_budget_service import (
    LLMBudgetExceeded,
    LLMPricing,
    estimate_cost_micros,
    register_pricing,
)
from agency.services.llm_runtime import LLMRuntimeError, complete_with_logging


def _seed(database_url, *, org_cap, client_cap):
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug="agency", llm_budget_micros=org_cap)
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    session.add(
        ClientLLMBudget(
            org_id=org.id,
            client_id=client.id,
            budget_micros=client_cap,
        )
    )
    session.commit()
    session.close()
    return org, client


def _priced_provider(call_counter):
    return type(
        "Provider",
        (),
        {
            "name": "test-paid",
            "default_model": "test-model",
            "complete": lambda self, request: (
                call_counter.append(request),
                LLMResponse(
                    content="ok",
                    model="test-model",
                    tokens_in=10,
                    tokens_out=100,
                ),
            )[1],
        },
    )()


def test_cost_estimate_is_deterministic():
    register_pricing("test-cost", "model", LLMPricing(100, 200))
    assert estimate_cost_micros(
        provider="test-cost",
        model="model",
        tokens_in=10,
        tokens_out=100,
    ) == 21


def test_org_budget_blocks_paid_call_before_provider_invocation(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'budget.db'}"
    org, client = _seed(database_url, org_cap=200, client_cap=1000)
    register_pricing("test-paid", "test-model", LLMPricing(100, 200))
    calls = []
    provider = _priced_provider(calls)
    monkeypatch.setattr("agency.services.llm_runtime.get_llm_provider", lambda name=None: provider)

    session = create_session_factory(database_url)()
    with pytest.raises(LLMRuntimeError, match="organization LLM budget exceeded"):
        complete_with_logging(
            session,
            org_id=org.id,
            client_id=client.id,
            agent="test-agent",
            request=LLMRequest(
                messages=(LLMMessage("user", "one two three"),),
                max_tokens=1000,
            ),
        )

    assert calls == []
    invocation = session.query(LLMInvocation).one()
    assert invocation.status == "budget_blocked"
    assert invocation.cost_micros == 0
    session.close()


def test_client_budget_blocks_paid_call_before_provider_invocation(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'budget.db'}"
    org, client = _seed(database_url, org_cap=1000, client_cap=200)
    register_pricing("test-paid", "test-model", LLMPricing(100, 200))
    calls = []
    provider = _priced_provider(calls)
    monkeypatch.setattr("agency.services.llm_runtime.get_llm_provider", lambda name=None: provider)

    session = create_session_factory(database_url)()
    with pytest.raises(LLMRuntimeError, match="client LLM budget exceeded"):
        complete_with_logging(
            session,
            org_id=org.id,
            client_id=client.id,
            agent="test-agent",
            request=LLMRequest(
                messages=(LLMMessage("user", "one two three"),),
                max_tokens=1000,
            ),
        )

    assert calls == []
    session.rollback()
    session.close()


def test_successful_call_records_actual_cost(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'budget.db'}"
    org, client = _seed(database_url, org_cap=1000, client_cap=1000)
    register_pricing("test-paid", "test-model", LLMPricing(100, 200))
    calls = []
    provider = _priced_provider(calls)
    monkeypatch.setattr("agency.services.llm_runtime.get_llm_provider", lambda name=None: provider)

    session = create_session_factory(database_url)()
    response = complete_with_logging(
        session,
        org_id=org.id,
        client_id=client.id,
        agent="test-agent",
        request=LLMRequest(
            messages=(LLMMessage("user", "one two three"),),
            max_tokens=100,
        ),
    )
    session.commit()

    assert response.content == "ok"
    invocation = session.query(LLMInvocation).one()
    assert invocation.tokens_in == 10
    assert invocation.tokens_out == 100
    assert invocation.cost_micros == 21
    session.close()
