import anyio
import httpx
from uuid import UUID

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, Client, ClientFact, Org
from agency.db.research_models import ResearchRun, ResearchSource
from agency.db.workflow_models import PipelineRun


def _request(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)
    return anyio.run(request)


def _seed_ready_for_research(database_url):
    create_all(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Praxis", slug="praxis", category="dental")
    session.add(client)
    session.flush()
    session.add(ClientFact(org_id=org.id, client_id=client.id, key="city", value="Nürnberg", value_type="text", source_kind="client", confidence=1, status="approved"))
    session.add(Artifact(org_id=org.id, artifact_type="business_facts", schema_version="1.0.0", payload_json={"client_id": str(client.id), "facts": [{"key": "city", "value": "Nürnberg"}]}))
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="FACTS_APPROVED"))
    session.commit()
    session.close()
    return org, client


def test_mock_research_creates_hashed_sources_and_report(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed_ready_for_research(database_url)
    app = create_app(database_url)

    response = _request(app, "/v1/research", {"org_id": str(org.id), "client_id": str(client.id), "provider": "mock"})
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "RESEARCH_COMPLETE"

    factory = create_session_factory(database_url)
    session = factory()
    artifact = session.get(Artifact, UUID(body["artifact_id"]))
    run = session.query(ResearchRun).filter(ResearchRun.client_id == client.id).one()
    sources = session.query(ResearchSource).filter(ResearchSource.research_run_id == run.id).all()
    pipeline = session.query(PipelineRun).filter(PipelineRun.client_id == client.id).one()
    assert artifact.artifact_type == "research_report"
    assert run.status == "complete" and run.provider == "mock"
    assert len(sources) == 3 and all(len(source.content_hash) == 64 for source in sources)
    assert pipeline.state == "RESEARCH_COMPLETE"
    session.close()


def test_research_approval_advances_gate(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed_ready_for_research(database_url)
    app = create_app(database_url)
    researched = _request(app, "/v1/research", {"org_id": str(org.id), "client_id": str(client.id)})
    artifact_id = researched.json()["artifact_id"]

    approved = _request(app, "/v1/research/approve", {
        "org_id": str(org.id), "client_id": str(client.id), "artifact_id": artifact_id,
        "approved_by": "owner@example.com",
    })
    assert approved.status_code == 200
    assert approved.json()["state"] == "RESEARCH_APPROVED"

    factory = create_session_factory(database_url)
    session = factory()
    approval = session.query(Approval).filter(Approval.artifact_id == UUID(artifact_id)).one()
    pipeline = session.query(PipelineRun).filter(PipelineRun.client_id == client.id).one()
    assert approval.gate == "RESEARCH" and approval.decision == "approved"
    assert pipeline.state == "RESEARCH_APPROVED"
    session.close()
