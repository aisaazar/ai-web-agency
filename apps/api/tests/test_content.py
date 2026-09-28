import json
from pathlib import Path

import anyio
import httpx
from uuid import UUID

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Artifact, Client, Org
from agency.db.workflow_models import PipelineRun


FIXTURE = Path(__file__).resolve().parents[3] / "sites" / "_template-base" / "content.dental-clinic.json"


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)
    return anyio.run(request)


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
    session.add(Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []}, revision=1, is_active=True,
    ))
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="RESEARCH_APPROVED"))
    session.commit()
    session.close()
    return org, client


def test_content_generation_validates_contract_and_completes(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed(database_url)
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload.update({"org_id": str(org.id), "client_id": str(client.id), "_fact_keys": []})
    response = _post(create_app(database_url), "/v1/content", payload)
    assert response.status_code == 201
    artifact_id = response.json()["id"]
    factory = create_session_factory(database_url)
    session = factory()
    artifact = session.get(Artifact, UUID(artifact_id))
    pipeline = session.query(PipelineRun).filter(PipelineRun.client_id == client.id).one()
    assert artifact is not None and artifact.artifact_type == "content_model"
    assert artifact.input_artifact_id is not None and pipeline.state == "CONTENT_COMPLETE"
    session.close()


def test_content_rejects_unapproved_fact_reference(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed(database_url)
    payload = {"org_id": str(org.id), "client_id": str(client.id), "_fact_keys": ["invented_fact"]}
    response = _post(create_app(database_url), "/v1/content", payload)
    assert response.status_code == 400 and "unapproved facts" in response.json()["detail"]


def test_content_rejects_forbidden_claim(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed(database_url)
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["hero"]["headline"] = "Die beste Behandlung garantiert Heilung"
    payload.update({"org_id": str(org.id), "client_id": str(client.id), "_fact_keys": []})
    response = _post(create_app(database_url), "/v1/content", payload)
    assert response.status_code == 400 and "claims policy" in response.json()["detail"]

def test_content_uses_business_facts_artifact_for_requested_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental A", slug="dental-a", category="dental")
    other = Client(org_id=org.id, name="Dental B", slug="dental-b", category="dental")
    session.add_all([client, other])
    session.flush()
    first = Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []}, revision=1, is_active=True,
    )
    second = Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(other.id), "facts": []}, revision=1, is_active=True,
    )
    session.add_all([first, second, PipelineRun(org_id=org.id, client_id=client.id, state="RESEARCH_APPROVED")])
    session.commit()
    session.close()

    import json
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload.update({"org_id": str(org.id), "client_id": str(client.id), "_fact_keys": []})
    response = _post(create_app(database_url), "/v1/content", payload)
    assert response.status_code == 201

    session = create_session_factory(database_url)()
    artifact = session.get(Artifact, UUID(response.json()["id"]))
    assert artifact is not None
    assert artifact.input_artifact_id == first.id
    session.close()