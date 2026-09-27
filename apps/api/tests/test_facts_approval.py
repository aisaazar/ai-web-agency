import anyio
import httpx
from uuid import UUID

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, Client, ClientFact, Org
from agency.db.workflow_models import PipelineRun


def _seed(database_url):
    create_all(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    for key, value in (("phone", "+49 911 1"), ("city", "Nürnberg")):
        session.add(ClientFact(org_id=org.id, client_id=client.id, key=key, value=value, value_type="text", source_kind="client", confidence=1))
    run = PipelineRun(org_id=org.id, client_id=client.id, state="FACTS_EXTRACTED")
    session.add(run)
    session.commit()
    session.close()
    return org, client, run


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)
    return anyio.run(request)


def test_facts_approval_creates_bound_artifact_and_advances_pipeline(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, _ = _seed(database_url)
    response = _post(create_app(database_url), "/v1/approvals/facts", {
        "org_id": str(org.id), "client_id": str(client.id), "approved_by": "owner@example.com",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "FACTS_APPROVED" and body["approved_fact_count"] == 2

    factory = create_session_factory(database_url)
    session = factory()
    artifact = session.get(Artifact, UUID(body["artifact_id"]))
    approval = session.query(Approval).filter(Approval.artifact_id == artifact.id).one()
    run = session.get(PipelineRun, UUID(body["pipeline_run_id"]))
    facts = session.query(ClientFact).filter(ClientFact.client_id == client.id).all()
    assert artifact.artifact_type == "business_facts"
    assert approval.gate == "FACTS" and approval.decision == "approved"
    assert run.state == "FACTS_APPROVED"
    assert all(f.status == "approved" for f in facts)
    session.close()


def test_facts_approval_is_tenant_scoped(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, _ = _seed(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    other = Org(name="Other", slug="other")
    session.add(other)
    session.commit()
    session.close()
    response = _post(create_app(database_url), "/v1/approvals/facts", {
        "org_id": str(other.id), "client_id": str(client.id), "approved_by": "owner@example.com",
    })
    assert response.status_code == 400
