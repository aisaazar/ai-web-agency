"""Client review loop: change request -> content revision -> rebuild -> resolve.

``/v1/review/*`` is the customer-facing "Client Review" step of the sellable flow
(Lead -> Demo -> Client Review -> Approval -> Build -> Preview -> Publish -> Rollback). It shipped
with the change-request table, service and router but without coverage, so this module pins the
guarantees the service docstring promises:

- a change request opens only against the site version that is *currently* built and already has a
  ready preview, so a review can never be attached to a stale or unreviewed build;
- a revision creates a new content artifact revision and archives - never mutates - the reviewed one;
- the ordinary content/design/build/preview gates still run, so no gate is bypassed;
- resolving pins the resulting build hash back to the change request for the audit trail.

Only the ``npm`` build step is replaced by a fixture bundle, exactly like
``test_client_preview_e2e.py``; every gate, transition and audit record is the real one.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import anyio
import httpx
import pytest

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Artifact, ChangeRequest, Org
from agency.providers.deploy import BUILD_COMPLETE_MARKER
from agency.providers.deploy import LocalStaticDeploymentProvider

FIXTURE = Path(__file__).resolve().parents[3] / "sites" / "_template-base" / "content.dental-clinic.json"


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)

    return anyio.run(request)


def _seed_org(database_url, *, slug="review-agency", name="Review Agency"):
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name=name, slug=slug)
    session.add(org)
    session.commit()
    session.refresh(org)
    session.close()
    return org


def _patch_build_and_preview(tmp_path, monkeypatch):
    """Real build/preview services; only the `npm` step becomes a fixture bundle."""
    import agency.api.deploy as deploy_api
    import agency.services.deploy_service as deploy_module
    import agency.services.site_build_service as build_module

    build_root = tmp_path / "builds"

    def fake_run(command, *, cwd, env):
        return True, f"mocked: {' '.join(command)}"

    def fake_persist(build_hash):
        destination = build_root / build_hash
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(
            "<!doctype html><html><body>review</body></html>", encoding="utf-8"
        )
        (destination / BUILD_COMPLETE_MARKER).write_text("ok\n", encoding="utf-8")
        return destination

    provider = LocalStaticDeploymentProvider(dist_root=tmp_path / "deploys")
    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", fake_persist)
    monkeypatch.setattr(deploy_module, "BUILD_BUNDLES_ROOT", build_root)
    monkeypatch.setattr(deploy_api, "get_deployment_provider", lambda _name="local_static": provider)
    monkeypatch.setattr(deploy_module, "get_deployment_provider", lambda _name="local_static": provider)


def _client_to_preview(app, *, org_id, client_slug):
    """Intake -> approvals -> content -> design -> build. Returns ids of the first build."""
    intake = _post(app, "/v1/intake", {
        "org_id": org_id,
        "client_name": "Praxis Review",
        "client_slug": client_slug,
        "category": "dental",
        "facts": [
            {"key": "phone", "value": "+49 911 123456", "source_kind": "client", "confidence": 1},
            {"key": "city", "value": "Nürnberg", "source_kind": "client", "confidence": 1},
        ],
    })
    assert intake.status_code == 201, intake.text
    client_id = intake.json()["client_id"]

    facts = _post(app, "/v1/approvals/facts", {
        "org_id": org_id, "client_id": client_id, "approved_by": "owner@example.com",
    })
    assert facts.status_code == 200, facts.text

    research = _post(app, "/v1/research", {"org_id": org_id, "client_id": client_id, "provider": "mock"})
    assert research.status_code == 201, research.text
    research_approved = _post(app, "/v1/research/approve", {
        "org_id": org_id,
        "client_id": client_id,
        "artifact_id": research.json()["artifact_id"],
        "approved_by": "owner@example.com",
    })
    assert research_approved.status_code == 200, research_approved.text

    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload.update({"org_id": org_id, "client_id": client_id, "_fact_keys": ["phone", "city"]})
    content = _post(app, "/v1/content", payload)
    assert content.status_code == 201, content.text
    content_id = content.json()["id"]
    content_approved = _post(app, "/v1/content/approve", {
        "org_id": org_id,
        "client_id": client_id,
        "artifact_id": content_id,
        "approved_by": "owner@example.com",
    })
    assert content_approved.status_code == 200, content_approved.text

    designed = _post(app, "/v1/design", {
        "org_id": org_id,
        "client_id": client_id,
        "content_artifact_id": content_id,
        "template_version": "1.0.0",
    })
    assert designed.status_code == 201, designed.text

    built = _post(app, "/v1/builds/site", {
        "org_id": org_id,
        "client_id": client_id,
        "content_artifact_id": content_id,
        "design_artifact_id": designed.json()["artifact_id"],
    })
    assert built.status_code == 201, built.text
    assert built.json()["state"] == "PREVIEW_READY"
    return client_id, content_id, built.json()


def _open_change_request(app, *, org_id, client_id, site_version_id):
    return _post(app, "/v1/review/request", {
        "org_id": org_id,
        "client_id": client_id,
        "site_version_id": site_version_id,
        "requested_by": "client@example.com",
        "body": "Bitte den Begruessungstext freundlicher formulieren.",
    })


# --- request ---------------------------------------------------------------------------------------------------


def test_change_request_pins_the_exact_reviewed_build(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    _patch_build_and_preview(tmp_path, monkeypatch)
    org_id = str(org.id)

    client_id, _, built = _client_to_preview(app, org_id=org_id, client_slug="praxis-pin")
    site_version_id = built["site_version_id"]

    # No preview deployment yet: a review must not open against an unreviewed build.
    too_early = _open_change_request(
        app, org_id=org_id, client_id=client_id, site_version_id=site_version_id
    )
    assert too_early.status_code == 400, too_early.text
    assert "preview deployment not found" in too_early.json()["detail"]

    preview = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_id, "site_version_id": site_version_id,
    })
    assert preview.status_code == 201, preview.text

    requested = _open_change_request(
        app, org_id=org_id, client_id=client_id, site_version_id=site_version_id
    )
    assert requested.status_code == 201, requested.text
    assert requested.json()["status"] == "open"
    change_request_id = requested.json()["change_request_id"]

    session = create_session_factory(database_url)()
    change_request = session.get(ChangeRequest, UUID(change_request_id))
    assert str(change_request.org_id) == org_id
    assert str(change_request.client_id) == client_id
    assert str(change_request.site_version_id) == site_version_id
    assert change_request.build_hash == built["build_hash"]
    assert change_request.requested_by == "client@example.com"
    assert change_request.resulting_content_artifact_id is None
    session.close()


# --- revision -> rebuild -> resolve ----------------------------------------------------------------------------


def test_revision_rebuild_and_resolve_preserves_reviewed_lineage(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    _patch_build_and_preview(tmp_path, monkeypatch)
    org_id = str(org.id)

    client_id, first_content_id, first_build = _client_to_preview(
        app, org_id=org_id, client_slug="praxis-revise"
    )
    first_version_id = first_build["site_version_id"]
    preview = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_id, "site_version_id": first_version_id,
    })
    assert preview.status_code == 201, preview.text

    requested = _open_change_request(
        app, org_id=org_id, client_id=client_id, site_version_id=first_version_id
    )
    assert requested.status_code == 201, requested.text
    change_request_id = requested.json()["change_request_id"]

    # A revision overrides content on top of the reviewed artifact, so the schema stays valid.
    reviewed = json.loads(FIXTURE.read_text(encoding="utf-8"))
    revision = _post(app, "/v1/review/revision", {
        "org_id": org_id,
        "client_id": client_id,
        "change_request_id": change_request_id,
        "approved_by": "owner@example.com",
        "site": {**reviewed["site"], "tagline": "Zahnmedizin neu gedacht"},
    })
    assert revision.status_code == 201, revision.text
    assert revision.json()["revision"] == 2
    second_content_id = revision.json()["content_artifact_id"]

    session = create_session_factory(database_url)()
    first_artifact = session.get(Artifact, UUID(first_content_id))
    second_artifact = session.get(Artifact, UUID(second_content_id))
    # The reviewed artifact is archived, never mutated, and the revision carries the new copy.
    assert first_artifact.is_active is False
    assert second_artifact.is_active is True
    assert second_artifact.revision == 2
    assert second_artifact.payload_json["site"]["tagline"] == "Zahnmedizin neu gedacht"
    assert first_artifact.payload_json["site"]["tagline"] != "Zahnmedizin neu gedacht"
    session.close()

    # The revision still has to pass the ordinary gates.
    approved = _post(app, "/v1/content/approve", {
        "org_id": org_id,
        "client_id": client_id,
        "artifact_id": second_content_id,
        "approved_by": "owner@example.com",
    })
    assert approved.status_code == 200, approved.text

    designed = _post(app, "/v1/design", {
        "org_id": org_id,
        "client_id": client_id,
        "content_artifact_id": second_content_id,
        "template_version": "1.0.0",
    })
    assert designed.status_code == 201, designed.text

    built = _post(app, "/v1/builds/site", {
        "org_id": org_id,
        "client_id": client_id,
        "content_artifact_id": second_content_id,
        "design_artifact_id": designed.json()["artifact_id"],
    })
    assert built.status_code == 201, built.text
    assert built.json()["state"] == "PREVIEW_READY"
    second_version_id = built.json()["site_version_id"]
    second_build_hash = built.json()["build_hash"]
    assert second_version_id != first_version_id
    assert second_build_hash != first_build["build_hash"]

    # A build hash that does not belong to the resulting version is refused.
    mismatched = _post(app, "/v1/review/resolve", {
        "org_id": org_id,
        "client_id": client_id,
        "change_request_id": change_request_id,
        "site_version_id": second_version_id,
        "build_hash": first_build["build_hash"],
        "approved_by": "owner@example.com",
    })
    assert mismatched.status_code == 400, mismatched.text
    assert "build_hash does not match site version" in mismatched.json()["detail"]

    second_preview = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_id, "site_version_id": second_version_id,
    })
    assert second_preview.status_code == 201, second_preview.text

    resolved = _post(app, "/v1/review/resolve", {
        "org_id": org_id,
        "client_id": client_id,
        "change_request_id": change_request_id,
        "site_version_id": second_version_id,
        "build_hash": second_build_hash,
        "approved_by": "owner@example.com",
        "decision": "resolved",
    })
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"

    session = create_session_factory(database_url)()
    change_request = session.get(ChangeRequest, UUID(change_request_id))
    # Lineage: the request still points at the reviewed version and now records the outcome.
    assert str(change_request.site_version_id) == first_version_id
    assert change_request.build_hash == first_build["build_hash"]
    assert str(change_request.resulting_content_artifact_id) == second_content_id
    assert change_request.resulting_build_hash == second_build_hash
    session.close()


# --- isolation + decision validation ---------------------------------------------------------------------------


def test_change_request_cannot_cross_tenant(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    other = _seed_org(database_url, slug="other-agency", name="Other Agency")
    app = create_app(database_url)
    _patch_build_and_preview(tmp_path, monkeypatch)
    org_id = str(org.id)

    client_id, _, built = _client_to_preview(app, org_id=org_id, client_slug="praxis-tenant")
    site_version_id = built["site_version_id"]
    preview = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_id, "site_version_id": site_version_id,
    })
    assert preview.status_code == 201, preview.text

    requested = _open_change_request(
        app, org_id=org_id, client_id=client_id, site_version_id=site_version_id
    )
    assert requested.status_code == 201, requested.text

    # Organisation B must not be able to resolve organisation A's change request.
    crossed = _post(app, "/v1/review/resolve", {
        "org_id": str(other.id),
        "client_id": client_id,
        "change_request_id": requested.json()["change_request_id"],
        "site_version_id": site_version_id,
        "build_hash": built["build_hash"],
        "approved_by": "owner@example.com",
    })
    assert crossed.status_code == 400, crossed.text


@pytest.mark.parametrize("decision", ["approved", "done"])
def test_resolve_rejects_unknown_decisions(tmp_path, monkeypatch, decision):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    _patch_build_and_preview(tmp_path, monkeypatch)
    org_id = str(org.id)

    client_id, _, built = _client_to_preview(app, org_id=org_id, client_slug="praxis-decision")
    site_version_id = built["site_version_id"]
    preview = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_id, "site_version_id": site_version_id,
    })
    assert preview.status_code == 201, preview.text

    requested = _open_change_request(
        app, org_id=org_id, client_id=client_id, site_version_id=site_version_id
    )
    assert requested.status_code == 201, requested.text

    rejected = _post(app, "/v1/review/resolve", {
        "org_id": org_id,
        "client_id": client_id,
        "change_request_id": requested.json()["change_request_id"],
        "site_version_id": site_version_id,
        "build_hash": built["build_hash"],
        "approved_by": "owner@example.com",
        "decision": decision,
    })
    # The decision enum is schema-validated, so an unknown value never reaches the service.
    assert rejected.status_code == 422, rejected.text