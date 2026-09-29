import json
from pathlib import Path
from uuid import UUID

import anyio
import httpx

from agency.api import create_app
from agency.db.auth_models import AuditLog
from agency.db.models import Deploy, Org, SiteVersion
from agency.db.session import create_all, create_session_factory
from agency.providers.deploy import LocalStaticDeploymentProvider


FIXTURE = Path(__file__).resolve().parents[3] / "sites" / "_template-base" / "content.dental-clinic.json"


def _request(app, method, path, **kwargs):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)
    return anyio.run(request)


def _seed_org(database_url):
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="E2E Agency", slug="e2e-agency")
    session.add(org)
    session.commit()
    session.close()
    return org


def test_complete_http_lifecycle_to_dashboard_and_rollback(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)

    import agency.services.site_build_service as build_module
    import agency.api.deploy as deploy_api
    import agency.services.deploy_service as deploy_module

    build_root = tmp_path / "builds"
    deploy_root = tmp_path / "deploys"

    def fake_run(command, *, cwd, env):
        return True, f"mocked: {' '.join(command)}"

    def fake_persist(build_hash):
        destination = build_root / build_hash
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(
            "<!doctype html><html><body>E2E</body></html>",
            encoding="utf-8",
        )
        return destination

    provider = LocalStaticDeploymentProvider(dist_root=deploy_root)
    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", fake_persist)
    monkeypatch.setattr(build_module, "BUILD_ROOT", build_root)
    monkeypatch.setattr(deploy_module, "BUILD_BUNDLES_ROOT", build_root)
    monkeypatch.setattr(deploy_api, "get_deployment_provider", lambda _name="local_static": provider)
    monkeypatch.setattr(deploy_module, "get_deployment_provider", lambda _name="local_static": provider)

    app = create_app(database_url)
    org_id = str(org.id)

    intake = _request(
        app,
        "POST",
        "/v1/intake",
        json={
            "org_id": org_id,
            "client_name": "Praxis E2E",
            "client_slug": "praxis-e2e",
            "category": "dental",
            "jurisdiction": "DE",
            "locale": "de-DE",
            "facts": [
                {
                    "key": "phone",
                    "value": "+49 911 123456",
                    "source_kind": "client",
                    "confidence": 1,
                },
                {
                    "key": "city",
                    "value": "Nürnberg",
                    "source_kind": "client",
                    "confidence": 1,
                },
            ],
        },
    )
    assert intake.status_code == 201
    client_id = intake.json()["client_id"]

    facts = _request(
        app,
        "POST",
        "/v1/approvals/facts",
        json={"org_id": org_id, "client_id": client_id, "approved_by": "owner@example.com"},
    )
    assert facts.status_code == 200
    assert facts.json()["state"] == "FACTS_APPROVED"

    research = _request(
        app,
        "POST",
        "/v1/research",
        json={"org_id": org_id, "client_id": client_id, "provider": "mock"},
    )
    assert research.status_code == 201
    research_id = research.json()["artifact_id"]

    research_approval = _request(
        app,
        "POST",
        "/v1/research/approve",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "artifact_id": research_id,
            "approved_by": "owner@example.com",
        },
    )
    assert research_approval.status_code == 200
    assert research_approval.json()["state"] == "RESEARCH_APPROVED"

    content = json.loads(FIXTURE.read_text(encoding="utf-8"))
    content.update({"org_id": org_id, "client_id": client_id, "_fact_keys": ["phone", "city"]})
    generated = _request(app, "POST", "/v1/content", json=content)
    assert generated.status_code == 201
    content_id = generated.json()["id"]

    content_approval = _request(
        app,
        "POST",
        "/v1/content/approve",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "artifact_id": content_id,
            "approved_by": "owner@example.com",
        },
    )
    assert content_approval.status_code == 200
    assert content_approval.json()["state"] == "CONTENT_APPROVED"

    design = _request(
        app,
        "POST",
        "/v1/design",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "content_artifact_id": content_id,
            "preset_id": "health",
            "template_version": "1.0.0",
        },
    )
    assert design.status_code == 201
    design_id = design.json()["artifact_id"]

    build = _request(
        app,
        "POST",
        "/v1/builds/site",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "content_artifact_id": content_id,
            "design_artifact_id": design_id,
        },
    )
    assert build.status_code == 201
    build_data = build.json()
    build_hash = build_data["build_hash"]

    preview = _request(
        app,
        "POST",
        "/v1/deploys/preview",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "site_version_id": build_data["site_version_id"],
        },
    )
    assert preview.status_code == 201
    assert preview.json()["state"] == "PREVIEW_READY"

    session = create_session_factory(database_url)()
    from agency.db.models import Artifact, Site

    build_artifact = session.query(Artifact).filter(
        Artifact.org_id == org.id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == build_hash,
    ).one()
    site = session.query(Site).filter(Site.org_id == org.id, Site.client_id == UUID(client_id)).one()
    session.close()

    publish_approval = _request(
        app,
        "POST",
        "/v1/publish/approve",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "build_artifact_id": str(build_artifact.id),
            "approved_by": "owner@example.com",
        },
    )
    assert publish_approval.status_code == 200
    assert publish_approval.json()["state"] == "PREVIEW_APPROVED"

    published = _request(
        app,
        "POST",
        "/v1/deploys/publish",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "site_version_id": build_data["site_version_id"],
        },
    )
    assert published.status_code == 201
    assert published.json()["state"] == "LIVE"
    deploy_id = published.json()["deploy_id"]

    domain = _request(
        app,
        "POST",
        "/v1/deploys/domain",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "fqdn": "WWW.Example.DE.",
        },
    )
    assert domain.status_code == 200
    assert domain.json() == {
        "provider": "local_static",
        "fqdn": "www.example.de",
        "status": "attached",
    }

    logs = _request(
        app,
        "POST",
        "/v1/deploys/logs",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "deploy_id": deploy_id,
        },
    )
    assert logs.status_code == 200
    assert logs.json()["deploy_id"] == deploy_id
    assert logs.json()["logs"].startswith("local_static build=")

    lead = _request(
        app,
        "POST",
        "/v1/leads",
        json={
            "site_id": str(site.id),
            "name": "Maria E2E",
            "email": "maria@example.com",
            "message": "Ich möchte einen Termin vereinbaren.",
            "consent": True,
        },
    )
    assert lead.status_code == 201

    leads = _request(app, "GET", f"/v1/leads?org_id={org_id}")
    assert leads.status_code == 200
    assert leads.json()[0]["name"] == "Maria E2E"

    dashboard = _request(app, "GET", f"/v1/dashboard/overview?org_id={org_id}")
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["counts"] == {"clients": 1, "artifacts": 5, "deployments": 2, "new_leads": 1}
    assert data["clients"][0]["state"] == "LIVE"
    assert data["clients"][0]["current_build_hash"] == build_hash
    assert data["leads"][0]["name"] == "Maria E2E"
    assert data["leads"][0]["email"] == "maria@example.com"
    assert data["deployments"][0]["status"] == "live"

    rollback = _request(
        app,
        "POST",
        "/v1/deploys/rollback",
        json={
            "org_id": org_id,
            "client_id": client_id,
            "build_hash": build_hash,
        },
    )
    assert rollback.status_code == 201
    assert rollback.json()["state"] == "LIVE"
    assert rollback.json()["build_hash"] == build_hash

    session = create_session_factory(database_url)()
    site_after = session.query(Site).filter(Site.org_id == org.id, Site.client_id == UUID(client_id)).one()
    production = session.query(Deploy).join(
        SiteVersion, SiteVersion.id == Deploy.site_version_id
    ).filter(
        Deploy.org_id == org.id,
        SiteVersion.site_id == site_after.id,
        Deploy.environment == "production",
    ).all()
    assert [row.status for row in production].count("live") == 1
    assert next(row for row in production if row.id == UUID(rollback.json()["deploy_id"])).status == "live"
    assert next(row for row in production if row.id == UUID(deploy_id)).status == "superseded"

    actions = {row.action for row in session.query(AuditLog).filter(AuditLog.org_id == org.id).all()}
    session.close()
    assert site_after.current_build_hash == build_hash
    assert {
        "approval.facts_approved",
        "approval.research_approved",
        "approval.content_approved",
        "approval.publish_approved",
        "deployment.preview_created",
        "deployment.published",
        "deployment.rolled_back",
    } <= actions
