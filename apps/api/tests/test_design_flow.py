import json
from pathlib import Path
from uuid import UUID

import anyio
import httpx

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, Client, Org
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
    session.add(Artifact(org_id=org.id, artifact_type="business_facts", schema_version="1.0.0", payload_json={"client_id": str(client.id), "facts": []}))
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="RESEARCH_APPROVED"))
    session.add(Artifact(org_id=org.id, artifact_type="research_report", schema_version="1.0.0", payload_json={"client_id": str(client.id), "sources": []}))
    session.commit()
    session.close()
    return org, client


def test_content_approval_then_design_advance_pipeline(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client = _seed(database_url)
    app = create_app(database_url)
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload.update({"org_id": str(org.id), "client_id": str(client.id), "_fact_keys": []})
    generated = _post(app, "/v1/content", payload)
    assert generated.status_code == 201
    content_id = generated.json()["id"]

    approved = _post(app, "/v1/content/approve", {
        "org_id": str(org.id), "client_id": str(client.id),
        "artifact_id": content_id, "approved_by": "owner@example.com",
    })
    assert approved.status_code == 200 and approved.json()["state"] == "CONTENT_APPROVED"

    designed = _post(app, "/v1/design", {
        "org_id": str(org.id), "client_id": str(client.id),
        "content_artifact_id": content_id, "preset_id": "health", "template_version": "1.0.0",
    })
    assert designed.status_code == 201 and designed.json()["state"] == "DESIGN_APPROVED"

    factory = create_session_factory(database_url)
    session = factory()
    design = session.get(Artifact, UUID(designed.json()["artifact_id"]))
    pipeline = session.query(PipelineRun).filter(PipelineRun.client_id == client.id).one()
    approvals = session.query(Approval).filter(Approval.artifact_id == UUID(content_id)).all()
    assert design is not None and design.artifact_type == "design_plan"
    assert pipeline.state == "DESIGN_APPROVED"
    assert approvals and approvals[0].gate == "CONTENT"
    session.close()
