import anyio
import httpx
from uuid import UUID

from agency.api import create_app
from agency.db import create_all
from agency.db.models import Client, ClientFact, Org
from agency.db.session import create_session_factory
from agency.db.workflow_models import PipelineRun


def _seed_org(database_url):
    create_all(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.commit()
    session.close()
    return org


def _request(database_url, payload):
    app = create_app(database_url)

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/v1/intake", json=payload)

    return anyio.run(request)


def test_intake_creates_client_facts_and_pipeline_state(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    response = _request(database_url, {
        "org_id": str(org.id), "client_name": "Praxis Morgenstern",
        "client_slug": "praxis-morgenstern", "category": "dental",
        "facts": [
            {"key": "phone", "value": "+49 911 123456", "source_kind": "client", "confidence": 1},
            {"key": "city", "value": "Nürnberg", "source_kind": "client", "confidence": 1},
        ],
    })
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "FACTS_EXTRACTED" and body["fact_count"] == 2

    factory = create_session_factory(database_url)
    session = factory()
    client = session.get(Client, UUID(body["client_id"]))
    facts = session.query(ClientFact).filter(ClientFact.client_id == client.id).all()
    run = session.get(PipelineRun, UUID(body["pipeline_run_id"]))
    assert client is not None and client.org_id == org.id
    assert len(facts) == 2 and all(fact.status == "proposed" for fact in facts)
    assert run is not None and run.state == "FACTS_EXTRACTED"
    session.close()


def test_intake_duplicate_slug_is_rejected(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    payload = {
        "org_id": str(org.id), "client_name": "One", "client_slug": "same",
        "category": "dental", "facts": [],
    }
    assert _request(database_url, payload).status_code == 201
    assert _request(database_url, {**payload, "client_name": "Two"}).status_code == 400
