import anyio
import httpx
from uuid import UUID

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, Client, ClientFact, Org
from agency.db.research_models import ResearchRun, ResearchSource
from agency.db.workflow_models import PipelineRun
from agency.providers.research import FetchedPage, Source


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


def test_existing_client_website_is_included_in_research(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed_ready_for_research(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    row = session.get(Client, client.id)
    row.existing_url = "https://client.example"
    session.commit()
    session.close()

    class FakeProvider:
        name = "fake"

        def search(self, query, *, max_results):
            return [
                Source(url="https://source.example", title="Search source", excerpt="Search evidence"),
                Source(url="https://client.example", title="Duplicate client URL", excerpt="Duplicate"),
            ][:max_results]

        def fetch(self, url):
            return FetchedPage(url=url, title="Client website" if "client.example" in url else "Search source", text="Website evidence with enough text.")

    monkeypatch.setattr("agency.services.research_service.get_research_provider", lambda _name: FakeProvider())
    monkeypatch.setattr("agency.services.research_service.validate_fetch_url", lambda url: url)
    from agency.services.research_service import run_research

    session = factory()
    artifact = run_research(session, org_id=org.id, client_id=client.id, provider_name="fake")
    session.commit()
    run = session.query(ResearchRun).filter(ResearchRun.client_id == client.id).one()
    sources = session.query(ResearchSource).filter(ResearchSource.research_run_id == run.id).all()
    session.close()

    urls = [item["url"] for item in artifact.payload_json["sources"]]
    assert urls.count("https://client.example") == 1
    assert "https://source.example" in urls
    assert len(sources) == 2
    assert run.query_plan_json["existing_url"] == "https://client.example"
    assert run.query_plan_json["existing_url_fetched"] is True


def test_existing_client_website_failure_is_non_fatal(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed_ready_for_research(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    row = session.get(Client, client.id)
    row.existing_url = "https://client.example"
    session.commit()
    session.close()

    class FakeProvider:
        name = "fake"

        def search(self, query, *, max_results):
            return [Source(url="https://source.example", title="Search source", excerpt="Search evidence")]

        def fetch(self, url):
            if url == "https://client.example":
                raise RuntimeError("site unavailable")
            return FetchedPage(url=url, title="Search source", text="Website evidence with enough text.")

    monkeypatch.setattr("agency.services.research_service.get_research_provider", lambda _name: FakeProvider())
    monkeypatch.setattr("agency.services.research_service.validate_fetch_url", lambda url: url)
    from agency.services.research_service import run_research

    session = factory()
    artifact = run_research(session, org_id=org.id, client_id=client.id, provider_name="fake")
    session.commit()
    run = session.query(ResearchRun).filter(ResearchRun.client_id == client.id).one()
    sources = session.query(ResearchSource).filter(ResearchSource.research_run_id == run.id).all()
    session.close()

    assert artifact.payload_json["sources"][0]["url"] == "https://source.example"
    assert len(sources) == 1
    assert run.query_plan_json["existing_url_fetched"] is False
    assert "site unavailable" in run.query_plan_json["existing_url_error"]
