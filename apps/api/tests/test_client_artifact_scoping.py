"""Workflow actions must never consume another client's artifact.

Artifacts are scoped to an organisation, not to a client, so the application layer has to prove that
the artifact named in a request belongs to the client whose pipeline is being advanced.
"""

from uuid import UUID

import anyio
import httpx

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, Client, Org, SiteVersion
from agency.db.workflow_models import PipelineRun


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)
    return anyio.run(request)


def _seed(database_url, *, state):
    """Two clients in one org, each with its own facts/content/design/research artifacts."""
    create_all(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental A", slug="dental-a", category="dental")
    other = Client(org_id=org.id, name="Dental B", slug="dental-b", category="dental")
    session.add_all([client, other])
    session.flush()

    facts_a = Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []}, revision=1, is_active=True,
    )
    facts_b = Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(other.id), "facts": []}, revision=1, is_active=True,
    )
    session.add_all([facts_a, facts_b])
    session.flush()

    content_b = Artifact(
        org_id=org.id, artifact_type="content_model", schema_version="1.0.0",
        payload_json={"content_schema_version": "1.0.0", "meta": {"client_slug": "dental-b"}},
        input_artifact_id=facts_b.id, revision=1, is_active=True,
    )
    design_b = Artifact(
        org_id=org.id, artifact_type="design_plan", schema_version="1.0.0",
        payload_json={
            "client_id": str(other.id),
            "template_version": "1.0.0",
            "design_preset_id": "health",
        },
        revision=1, is_active=True,
    )
    report_b = Artifact(
        org_id=org.id, artifact_type="research_report", schema_version="1.0.0",
        payload_json={"client_id": str(other.id), "sources": []}, revision=1, is_active=True,
    )
    session.add_all([content_b, design_b, report_b])
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state=state))
    session.commit()

    ids = {
        "org": str(org.id),
        "client": str(client.id),
        "other": str(other.id),
        "content": str(content_b.id),
        "design": str(design_b.id),
        "report": str(report_b.id),
    }
    session.close()
    return ids


def _pipeline_state(database_url, client_id):
    session = create_session_factory(database_url)()
    run = session.query(PipelineRun).filter(
        PipelineRun.client_id == UUID(client_id)
    ).order_by(PipelineRun.created_at.desc()).first()
    state = run.state if run else None
    session.close()
    return state


def test_content_approval_rejects_artifact_from_another_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed(database_url, state="CONTENT_COMPLETE")
    response = _post(create_app(database_url), "/v1/content/approve", {
        "org_id": ids["org"], "client_id": ids["client"],
        "artifact_id": ids["content"], "approved_by": "owner@example.com",
    })
    assert response.status_code == 400
    assert _pipeline_state(database_url, ids["client"]) == "CONTENT_COMPLETE"
    session = create_session_factory(database_url)()
    assert session.query(Approval).filter(Approval.gate == "CONTENT").count() == 0
    session.close()


def test_research_approval_rejects_report_from_another_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed(database_url, state="RESEARCH_COMPLETE")
    response = _post(create_app(database_url), "/v1/research/approve", {
        "org_id": ids["org"], "client_id": ids["client"],
        "artifact_id": ids["report"], "approved_by": "owner@example.com",
    })
    assert response.status_code == 400
    assert _pipeline_state(database_url, ids["client"]) == "RESEARCH_COMPLETE"


def test_design_rejects_content_artifact_from_another_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed(database_url, state="CONTENT_APPROVED")
    response = _post(create_app(database_url), "/v1/design", {
        "org_id": ids["org"], "client_id": ids["client"],
        "content_artifact_id": ids["content"], "preset_id": "health",
        "template_version": "1.0.0",
    })
    assert response.status_code == 400
    assert _pipeline_state(database_url, ids["client"]) == "CONTENT_APPROVED"
    session = create_session_factory(database_url)()
    assert session.query(Artifact).filter(Artifact.artifact_type == "design_plan").count() == 1
    session.close()


def test_site_build_rejects_artifacts_from_another_client(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed(database_url, state="DESIGN_APPROVED")

    import agency.services.site_build_service as build_module

    calls: list[list[str]] = []

    def recording_run(command, *, cwd, env):
        calls.append(list(command))
        return True, f"mocked: {' '.join(command)}"

    monkeypatch.setattr(build_module, "_run", recording_run)

    response = _post(create_app(database_url), "/v1/builds/site", {
        "org_id": ids["org"], "client_id": ids["client"],
        "content_artifact_id": ids["content"], "design_artifact_id": ids["design"],
    })
    assert response.status_code == 400
    assert calls == [], "a cross-client artifact must be rejected before any build command runs"
    assert _pipeline_state(database_url, ids["client"]) == "DESIGN_APPROVED"
    session = create_session_factory(database_url)()
    assert session.query(SiteVersion).count() == 0
    session.close()

