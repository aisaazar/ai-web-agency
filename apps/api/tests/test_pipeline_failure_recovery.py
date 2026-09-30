"""A failed AI step must stay observable, retryable and accounted for.

Regression coverage for two release blockers:
1. `get_db` rolls back the whole transaction when an endpoint raises, so the FAILED state,
   its audit entry and the cost of LLM calls that really happened used to vanish together.
   Discarded cost means `enforce_budget` under-counts spend on every failure.
2. FAILED had no outgoing transition at all, so a persisted failure would wedge a client.
"""
import json
from pathlib import Path

import anyio
import httpx
import pytest

from agency.api import create_app
from agency.db.auth_models import AuditLog
from agency.db.llm_budget_models import ClientLLMBudget
from agency.db.models import Artifact, Client, ClientFact, LLMInvocation, Org
from agency.db.session import create_all, create_session_factory
from agency.db.workflow_models import PipelineRun
from agency.domain.pipeline_definition import ALLOWED_TRANSITIONS
from agency.providers.llm import LLMResponse
from agency.services import llm_budget_service
from agency.services.llm_budget_service import LLMPricing, estimate_cost_micros
from agency.services.pipeline_service import PipelineError, transition

FIXTURE = Path(__file__).resolve().parents[3] / "sites" / "_template-base" / "content.dental-clinic.json"

PROVIDER = "test-paid"
MODEL = "test-model"
TEST_PRICING = LLMPricing(100, 200)
TOKENS_IN = 10
TOKENS_OUT = 100


@pytest.fixture(autouse=True)
def price_the_test_provider(monkeypatch):
    monkeypatch.setitem(llm_budget_service.PRICING, (PROVIDER, MODEL), TEST_PRICING)


def _provider_returning(content):
    return type(
        "Provider",
        (),
        {
            "name": PROVIDER,
            "default_model": MODEL,
            "complete": lambda self, request: LLMResponse(
                content=content, model=MODEL, tokens_in=TOKENS_IN, tokens_out=TOKENS_OUT
            ),
        },
    )()


def _seed(database_url, state="RESEARCH_APPROVED"):
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug="agency", llm_budget_micros=10_000_000)
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    session.add_all([
        ClientLLMBudget(org_id=org.id, client_id=client.id, budget_micros=10_000_000),
        Artifact(
            org_id=org.id,
            artifact_type="business_facts",
            schema_version="1.0.0",
            payload_json={"client_id": str(client.id), "facts": []},
            revision=1,
            is_active=True,
        ),
        ClientFact(
            org_id=org.id,
            client_id=client.id,
            key="practice.name",
            value="Dental",
            value_type="string",
            source_kind="intake",
            confidence=1.0,
            status="approved",
        ),
        PipelineRun(org_id=org.id, client_id=client.id, state=state),
    ])
    session.commit()
    session.close()
    return org, client


def _generate(app, org, client):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            return await http.post("/v1/content", json={
                "org_id": str(org.id),
                "client_id": str(client.id),
                "mode": "llm",
                "instruction": "Create the complete site content.",
            })
    return anyio.run(request)


def _valid_content():
    return json.dumps(json.loads(FIXTURE.read_text(encoding="utf-8")), ensure_ascii=False)


def _broken_provider(monkeypatch):
    monkeypatch.setattr(
        "agency.services.llm_runtime.get_llm_provider", lambda name=None: _provider_returning("not-json")
    )


def test_content_failure_persists_failed_state_and_reason(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'fail.db'}"
    org, client = _seed(database_url)
    _broken_provider(monkeypatch)

    response = _generate(create_app(database_url), org, client)

    assert response.status_code == 400
    session = create_session_factory(database_url)()
    pipeline = session.query(PipelineRun).filter_by(client_id=client.id).one()
    assert pipeline.state == "FAILED", "the failure must be visible to operators"
    assert session.query(Artifact).filter(Artifact.artifact_type == "content_model").count() == 0
    entry = session.query(AuditLog).filter(
        AuditLog.action == "pipeline.content_generation_failed"
    ).one()
    assert entry.before_json == {"state": "CONTENT_GENERATING"}
    assert entry.after_json["state"] == "FAILED"
    assert entry.after_json["client_id"] == str(client.id)
    assert entry.after_json["reason"] == "LLM did not return valid JSON"
    session.close()


def test_failed_generation_still_accounts_paid_llm_cost(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'cost.db'}"
    org, client = _seed(database_url)
    _broken_provider(monkeypatch)
    app = create_app(database_url)
    per_call = estimate_cost_micros(
        provider=PROVIDER, model=MODEL, tokens_in=TOKENS_IN, tokens_out=TOKENS_OUT
    )
    assert per_call > 0

    # max_retries=1: two real provider calls per request, two requests.
    assert _generate(app, org, client).status_code == 400
    assert _generate(app, org, client).status_code == 400

    session = create_session_factory(database_url)()
    rows = session.query(LLMInvocation).filter_by(org_id=org.id, status="completed").all()
    assert len(rows) == 4
    # Budget enforcement sums these rows: if they were rolled back, repeated failures
    # would let paid spend grow without limit.
    assert sum(row.cost_micros for row in rows) == 4 * per_call
    session.close()


def test_failed_content_step_can_be_retried_to_success(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'retry.db'}"
    org, client = _seed(database_url)
    app = create_app(database_url)
    _broken_provider(monkeypatch)
    assert _generate(app, org, client).status_code == 400

    monkeypatch.setattr(
        "agency.services.llm_runtime.get_llm_provider",
        lambda name=None: _provider_returning(_valid_content()),
    )
    retry = _generate(app, org, client)

    assert retry.status_code == 201
    session = create_session_factory(database_url)()
    assert session.query(PipelineRun).filter_by(client_id=client.id).one().state == "CONTENT_COMPLETE"
    assert session.query(Artifact).filter(Artifact.artifact_type == "content_model").count() == 1
    session.close()


@pytest.mark.parametrize("state", ["INTAKE", "CONTENT_COMPLETE", "PREVIEW_APPROVED", "LIVE"])
def test_content_generation_still_rejects_non_retryable_states(tmp_path, monkeypatch, state):
    database_url = f"sqlite:///{tmp_path / 'guard.db'}"
    org, client = _seed(database_url, state=state)
    monkeypatch.setattr(
        "agency.services.llm_runtime.get_llm_provider",
        lambda name=None: _provider_returning(_valid_content()),
    )

    response = _generate(create_app(database_url), org, client)

    assert response.status_code == 400
    assert "not ready for content generation" in response.json()["detail"]
    session = create_session_factory(database_url)()
    assert session.query(PipelineRun).filter_by(client_id=client.id).one().state == state
    assert session.query(Artifact).filter(Artifact.artifact_type == "content_model").count() == 0
    session.close()


def test_failed_state_offers_only_recovery_transitions():
    assert set(ALLOWED_TRANSITIONS["FAILED"]) == {"CONTENT_GENERATING", "DESIGNING"}
    assert transition("FAILED", "CONTENT_GENERATING").to_state == "CONTENT_GENERATING"


@pytest.mark.parametrize(
    "to_state",
    ["CONTENT_APPROVED", "DESIGN_APPROVED", "BUILD_COMPLETE", "PREVIEW_APPROVED", "PUBLISHING", "LIVE"],
)
def test_failed_state_cannot_be_used_to_skip_approval_gates(to_state):
    with pytest.raises(PipelineError, match="Invalid pipeline transition"):
        transition("FAILED", to_state)

