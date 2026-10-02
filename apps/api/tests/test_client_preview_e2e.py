"""Client-specific preview E2E: intake selection -> design -> build -> preview URL.

A gallery selection that only exists as dashboard UI state is worthless. These tests walk the real
HTTP path - intake, approvals, design, build, preview - with only the `npm` build step replaced by a
fixture bundle, and prove that the client's `selected_preset_id`:

- is persisted tenant-scoped and rejected when unsupported,
- is what the design operation uses instead of silently defaulting to `health`,
- reaches the build (design token compilation + build artifact + site version),
- is what the preview deployment serves, at a URL naming exactly that build.

Tenant isolation cases prove organization A can never read or consume organization B's client,
artifact, selection or preview.
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
from agency.db.models import Artifact, Client, ClientFact, Deploy, Org, Site, SiteVersion
from agency.db.workflow_models import PipelineRun
from agency.providers.deploy import LocalStaticDeploymentProvider

FIXTURE = Path(__file__).resolve().parents[3] / "sites" / "_template-base" / "content.dental-clinic.json"
SUPPORTED_PRESETS = ("health", "corporate", "warm")


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)

    return anyio.run(request)


def _get(app, path):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return anyio.run(request)


def _seed_org(database_url, *, slug="agency", name="Agency"):
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name=name, slug=slug)
    session.add(org)
    session.commit()
    session.refresh(org)
    session.close()
    return org


def _intake_payload(org_id, client_slug, *, preset=None, facts=()):
    payload_facts = [
        {"key": "phone", "value": "+49 911 123456", "source_kind": "client", "confidence": 1},
        {"key": "city", "value": "Nürnberg", "source_kind": "client", "confidence": 1},
        *facts,
    ]
    if preset is not None:
        payload_facts.append({
            "key": "selected_preset_id",
            "value": preset,
            "value_type": "text",
            "source_kind": "dashboard",
            "source_ref": "template-gallery",
            "confidence": 1,
        })
    return {
        "org_id": org_id,
        "client_name": "Praxis Preview",
        "client_slug": client_slug,
        "category": "dental",
        "facts": payload_facts,
    }


def _content_payload(org_id, client_id):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload.update({"org_id": org_id, "client_id": client_id, "_fact_keys": ["phone", "city"]})
    return payload


def _flow_to_content_approved(app, *, org_id, client_slug, preset=None):
    """Intake -> facts -> research -> content, ending in the state design expects."""
    intake = _post(app, "/v1/intake", _intake_payload(org_id, client_slug, preset=preset))
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

    content = _post(app, "/v1/content", _content_payload(org_id, client_id))
    assert content.status_code == 201, content.text
    content_id = content.json()["id"]
    content_approved = _post(app, "/v1/content/approve", {
        "org_id": org_id,
        "client_id": client_id,
        "artifact_id": content_id,
        "approved_by": "owner@example.com",
    })
    assert content_approved.status_code == 200, content_approved.text
    return client_id, content_id


def _design(app, *, org_id, client_id, content_id, **extra):
    return _post(app, "/v1/design", {
        "org_id": org_id,
        "client_id": client_id,
        "content_artifact_id": content_id,
        "template_version": "1.0.0",
        **extra,
    })


def _patch_pipeline_artifacts(tmp_path, monkeypatch):
    """Real build + preview services; only the `npm` step becomes a fixture bundle.

    Returns the build environment captured by the mocked command so a test can assert which design
    preset the static template was actually asked to compile.
    """
    import agency.api.deploy as deploy_api
    import agency.services.deploy_service as deploy_module
    import agency.services.site_build_service as build_module

    build_root = tmp_path / "builds"
    captured: dict[str, str] = {}

    def fake_run(command, *, cwd, env):
        captured["command"] = " ".join(command)
        captured["preset"] = env.get("DESIGN_PRESET_ID", "")
        captured["content_file"] = env.get("CONTENT_FILE", "")
        captured["client_id"] = env.get("NEXT_PUBLIC_AGENCY_CLIENT_ID", "")
        return True, f"mocked: {' '.join(command)}"

    def fake_persist(build_hash):
        destination = build_root / build_hash
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index.html").write_text(
            "<!doctype html><html><body>preview</body></html>", encoding="utf-8"
        )
        return destination

    provider = LocalStaticDeploymentProvider(dist_root=tmp_path / "deploys")
    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", fake_persist)
    monkeypatch.setattr(deploy_module, "BUILD_BUNDLES_ROOT", build_root)
    monkeypatch.setattr(deploy_api, "get_deployment_provider", lambda _name="local_static": provider)
    monkeypatch.setattr(deploy_module, "get_deployment_provider", lambda _name="local_static": provider)
    return captured


def _design_preset(database_url, artifact_id) -> str:
    session = create_session_factory(database_url)()
    artifact = session.get(Artifact, UUID(artifact_id))
    preset = artifact.payload_json["design_preset_id"]
    session.close()
    return preset


def _pipeline_state(database_url, client_id) -> str | None:
    session = create_session_factory(database_url)()
    run = session.query(PipelineRun).filter(
        PipelineRun.client_id == UUID(client_id)
    ).order_by(PipelineRun.created_at.desc()).first()
    state = run.state if run else None
    session.close()
    return state


def _design_artifact_count(database_url) -> int:
    session = create_session_factory(database_url)()
    count = session.query(Artifact).filter(Artifact.artifact_type == "design_plan").count()
    session.close()
    return count


# --- intake ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("preset", SUPPORTED_PRESETS)
def test_intake_persists_selected_preset_as_tenant_scoped_fact(tmp_path, preset):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    org_id = str(org.id)

    response = _post(app, "/v1/intake", _intake_payload(org_id, f"praxis-{preset}", preset=preset))
    assert response.status_code == 201, response.text
    client_id = response.json()["client_id"]

    session = create_session_factory(database_url)()
    fact = session.query(ClientFact).filter(
        ClientFact.key == "selected_preset_id",
        ClientFact.client_id == UUID(client_id),
    ).one()
    assert str(fact.org_id) == org_id
    assert fact.value == preset
    assert fact.value_type == "text"
    assert fact.source_kind == "dashboard"
    assert fact.source_ref == "template-gallery"
    assert fact.status == "proposed"
    session.close()

    # Retrieval: the dashboard detail endpoint hands the same selection back to the design stage.
    detail = _get(app, f"/v1/dashboard/clients/{client_id}?org_id={org_id}")
    assert detail.status_code == 200
    selections = [
        item for item in detail.json()["facts"] if item["key"] == "selected_preset_id"
    ]
    assert [item["value"] for item in selections] == [preset]


@pytest.mark.parametrize("preset", ["brutalist", "Minimal", "health ", "corporate-alt"])
def test_intake_rejects_unsupported_selected_preset(tmp_path, preset):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)

    response = _post(
        app, "/v1/intake", _intake_payload(str(org.id), "praxis-invalid", preset=preset)
    )
    assert response.status_code == 400
    assert "selected_preset_id" in response.json()["detail"]

    session = create_session_factory(database_url)()
    assert session.query(Client).count() == 0
    assert session.query(ClientFact).count() == 0
    assert session.query(PipelineRun).count() == 0
    session.close()


def test_intake_rejects_repeated_selected_preset(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    duplicate = {
        "key": "selected_preset_id",
        "value": "health",
        "value_type": "text",
        "source_kind": "dashboard",
        "source_ref": "template-gallery",
        "confidence": 1,
    }

    response = _post(
        app,
        "/v1/intake",
        _intake_payload(str(org.id), "praxis-duplicate", preset="corporate", facts=[duplicate]),
    )
    assert response.status_code == 400
    assert "at most once" in response.json()["detail"]

    session = create_session_factory(database_url)()
    assert session.query(Client).count() == 0
    session.close()


# --- design ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("preset", ["corporate", "warm"])
def test_design_uses_clients_selected_preset_when_request_omits_one(tmp_path, preset):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    org_id = str(org.id)

    client_id, content_id = _flow_to_content_approved(
        app, org_id=org_id, client_slug=f"praxis-{preset}", preset=preset
    )

    designed = _design(app, org_id=org_id, client_id=client_id, content_id=content_id)
    assert designed.status_code == 201, designed.text
    assert designed.json()["state"] == "DESIGN_APPROVED"
    assert _design_preset(database_url, designed.json()["artifact_id"]) == preset
    assert _pipeline_state(database_url, client_id) == "DESIGN_APPROVED"


def test_design_without_intake_selection_keeps_health_default(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    org_id = str(org.id)

    client_id, content_id = _flow_to_content_approved(
        app, org_id=org_id, client_slug="praxis-no-selection"
    )

    designed = _design(app, org_id=org_id, client_id=client_id, content_id=content_id)
    assert designed.status_code == 201, designed.text
    assert _design_preset(database_url, designed.json()["artifact_id"]) == "health"


def test_design_explicit_preset_still_wins(tmp_path):
    """The dashboard's design action may deliberately override the intake selection."""
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    org_id = str(org.id)

    client_id, content_id = _flow_to_content_approved(
        app, org_id=org_id, client_slug="praxis-override", preset="warm"
    )

    designed = _design(
        app, org_id=org_id, client_id=client_id, content_id=content_id, preset_id="corporate"
    )
    assert designed.status_code == 201, designed.text
    assert _design_preset(database_url, designed.json()["artifact_id"]) == "corporate"


def test_design_rejects_unknown_preset_id(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    org_id = str(org.id)

    client_id, content_id = _flow_to_content_approved(
        app, org_id=org_id, client_slug="praxis-bad-preset", preset="warm"
    )

    designed = _design(
        app, org_id=org_id, client_id=client_id, content_id=content_id, preset_id="brutalist"
    )
    assert designed.status_code == 400
    assert "unknown design preset" in designed.json()["detail"]
    assert _pipeline_state(database_url, client_id) == "CONTENT_APPROVED"
    assert _design_artifact_count(database_url) == 0


# --- build + preview ------------------------------------------------------------------------------------------


@pytest.mark.parametrize("preset", SUPPORTED_PRESETS)
def test_selected_preset_flows_from_intake_to_preview_url(tmp_path, monkeypatch, preset):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    captured = _patch_pipeline_artifacts(tmp_path, monkeypatch)
    org_id = str(org.id)

    client_id, content_id = _flow_to_content_approved(
        app, org_id=org_id, client_slug=f"praxis-e2e-{preset}", preset=preset
    )

    designed = _design(app, org_id=org_id, client_id=client_id, content_id=content_id)
    assert designed.status_code == 201, designed.text

    built = _post(app, "/v1/builds/site", {
        "org_id": org_id,
        "client_id": client_id,
        "content_artifact_id": content_id,
        "design_artifact_id": designed.json()["artifact_id"],
    })
    assert built.status_code == 201, built.text
    build_hash = built.json()["build_hash"]
    site_version_id = built.json()["site_version_id"]
    assert built.json()["state"] == "PREVIEW_READY"

    # The static template build compiled exactly the client's preset, for exactly this client.
    assert captured["preset"] == preset
    assert captured["client_id"] == client_id
    assert captured["content_file"] == f"content.generated.{client_id}.json"

    session = create_session_factory(database_url)()
    design = session.get(Artifact, UUID(designed.json()["artifact_id"]))
    version = session.get(SiteVersion, UUID(site_version_id))
    site = session.query(Site).filter(
        Site.org_id == org.id, Site.client_id == UUID(client_id)
    ).one()
    build_artifact = session.query(Artifact).filter(
        Artifact.org_id == org.id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == build_hash,
    ).one()
    assert design.payload_json["design_preset_id"] == preset
    assert version.design_preset_id == preset
    assert site.design_preset_id == preset
    assert version.build_hash == build_hash
    assert build_artifact.payload_json["design_preset_id"] == preset
    assert build_artifact.payload_json["site_version_id"] == site_version_id
    session.close()

    preview = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_id, "site_version_id": site_version_id,
    })
    assert preview.status_code == 201, preview.text
    assert preview.json()["state"] == "PREVIEW_READY"
    assert preview.json()["site_version_id"] == site_version_id

    # The preview URL names this client's exact build, and that bundle exists on disk.
    preview_url = preview.json()["url"]
    assert preview_url.endswith(f"/{build_hash}/index.html")
    assert (tmp_path / "deploys" / build_hash / "index.html").is_file()

    session = create_session_factory(database_url)()
    deploy = session.query(Deploy).filter(
        Deploy.org_id == org.id, Deploy.environment == "preview"
    ).one()
    assert str(deploy.site_version_id) == site_version_id
    assert deploy.status == "preview_ready"
    assert deploy.url == preview_url
    session.close()


def test_preview_rejects_other_clients_site_version(tmp_path, monkeypatch):
    """A preview is created for the requesting client's site version only."""
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org = _seed_org(database_url)
    app = create_app(database_url)
    captured = _patch_pipeline_artifacts(tmp_path, monkeypatch)
    org_id = str(org.id)

    client_a, content_a = _flow_to_content_approved(
        app, org_id=org_id, client_slug="praxis-a", preset="warm"
    )
    client_b = _flow_to_content_approved(
        app, org_id=org_id, client_slug="praxis-b", preset="corporate"
    )[0]

    designed_a = _design(app, org_id=org_id, client_id=client_a, content_id=content_a)
    built_a = _post(app, "/v1/builds/site", {
        "org_id": org_id, "client_id": client_a,
        "content_artifact_id": content_a, "design_artifact_id": designed_a.json()["artifact_id"],
    })
    assert built_a.status_code == 201, built_a.text
    assert captured["preset"] == "warm"

    rejected = _post(app, "/v1/deploys/preview", {
        "org_id": org_id, "client_id": client_b,
        "site_version_id": built_a.json()["site_version_id"],
    })
    assert rejected.status_code == 400

    session = create_session_factory(database_url)()
    assert session.query(Deploy).count() == 0
    session.close()


# --- tenant isolation -----------------------------------------------------------------------------------------


def _seed_pipeline_client(session, *, org, slug, preset=None):
    """A client parked at CONTENT_APPROVED with its own facts/content artifacts."""
    client = Client(org_id=org.id, name=f"Praxis {slug}", slug=slug, category="dental")
    session.add(client)
    session.flush()

    facts = Artifact(
        org_id=org.id, artifact_type="business_facts", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []}, revision=1, is_active=True,
    )
    session.add(facts)
    session.flush()
    content = Artifact(
        org_id=org.id, artifact_type="content_model", schema_version="1.0.0",
        payload_json={"content_schema_version": "1.0.0", "meta": {"client_slug": slug}},
        input_artifact_id=facts.id, revision=1, is_active=True,
    )
    session.add(content)
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="CONTENT_APPROVED"))
    if preset is not None:
        session.add(ClientFact(
            org_id=org.id, client_id=client.id, key="selected_preset_id", value=preset,
            value_type="text", source_kind="dashboard", source_ref="template-gallery", confidence=1,
        ))
    session.flush()
    return client, content


def _seed_two_tenants(database_url):
    """Organization A without a selection, organization B with `warm` selected."""
    create_all(database_url)
    session = create_session_factory(database_url)()
    org_a = Org(name="Tenant A", slug="tenant-a")
    org_b = Org(name="Tenant B", slug="tenant-b")
    session.add_all([org_a, org_b])
    session.flush()
    client_a, content_a = _seed_pipeline_client(session, org=org_a, slug="tenant-a-clinic")
    client_b, content_b = _seed_pipeline_client(
        session, org=org_b, slug="tenant-b-clinic", preset="warm"
    )
    session.commit()
    ids = {
        "org_a": str(org_a.id),
        "org_b": str(org_b.id),
        "client_a": str(client_a.id),
        "client_b": str(client_b.id),
        "content_a": str(content_a.id),
        "content_b": str(content_b.id),
    }
    session.close()
    return ids


def test_design_never_reads_another_tenants_selected_preset(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed_two_tenants(database_url)
    app = create_app(database_url)

    # Organization A's client never selected a style: it must not inherit organization B's `warm`.
    design_a = _design(
        app, org_id=ids["org_a"], client_id=ids["client_a"], content_id=ids["content_a"]
    )
    assert design_a.status_code == 201, design_a.text
    assert _design_preset(database_url, design_a.json()["artifact_id"]) == "health"

    # Organization B still gets its own selection.
    design_b = _design(
        app, org_id=ids["org_b"], client_id=ids["client_b"], content_id=ids["content_b"]
    )
    assert design_b.status_code == 201, design_b.text
    assert _design_preset(database_url, design_b.json()["artifact_id"]) == "warm"


def test_design_rejects_another_tenants_content_artifact(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed_two_tenants(database_url)
    app = create_app(database_url)

    rejected = _design(
        app, org_id=ids["org_a"], client_id=ids["client_a"], content_id=ids["content_b"]
    )
    assert rejected.status_code == 400
    assert _pipeline_state(database_url, ids["client_a"]) == "CONTENT_APPROVED"
    assert _design_artifact_count(database_url) == 0


def test_preview_rejects_another_tenants_site_version(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed_two_tenants(database_url)
    _patch_pipeline_artifacts(tmp_path, monkeypatch)

    session = create_session_factory(database_url)()
    site_b = Site(
        org_id=UUID(ids["org_b"]), client_id=UUID(ids["client_b"]),
        template_id="_template-base", design_preset_id="warm",
    )
    session.add(site_b)
    session.flush()
    version_b = SiteVersion(
        org_id=UUID(ids["org_b"]), site_id=site_b.id, build_hash="b" * 64,
        content_artifact_id=UUID(ids["content_b"]), content_schema_version="1.0.0",
        template_version="1.0.0", design_preset_id="warm",
    )
    session.add(version_b)
    session.commit()
    version_b_id = str(version_b.id)
    session.close()

    app = create_app(database_url)
    rejected = _post(app, "/v1/deploys/preview", {
        "org_id": ids["org_a"], "client_id": ids["client_a"], "site_version_id": version_b_id,
    })
    assert rejected.status_code == 400
    assert "site version not found" in rejected.json()["detail"]

    session = create_session_factory(database_url)()
    assert session.query(Deploy).count() == 0
    session.close()


def test_client_detail_never_exposes_another_tenants_client_or_selection(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed_two_tenants(database_url)
    app = create_app(database_url)

    own = _get(app, f"/v1/dashboard/clients/{ids['client_a']}?org_id={ids['org_a']}")
    assert own.status_code == 200
    assert own.json()["facts"] == []

    foreign = _get(app, f"/v1/dashboard/clients/{ids['client_b']}?org_id={ids['org_a']}")
    assert foreign.status_code == 404

    other_tenant = _get(app, f"/v1/dashboard/clients/{ids['client_b']}?org_id={ids['org_b']}")
    assert other_tenant.status_code == 200
    selections = [
        item for item in other_tenant.json()["facts"] if item["key"] == "selected_preset_id"
    ]
    assert [item["value"] for item in selections] == ["warm"]


def test_intake_writes_only_into_the_requesting_organization(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    ids = _seed_two_tenants(database_url)
    app = create_app(database_url)

    response = _post(
        app, "/v1/intake", _intake_payload(ids["org_a"], "tenant-a-second", preset="corporate")
    )
    assert response.status_code == 201, response.text
    client_id = response.json()["client_id"]

    session = create_session_factory(database_url)()
    fact = session.query(ClientFact).filter(
        ClientFact.client_id == UUID(client_id), ClientFact.key == "selected_preset_id"
    ).one()
    assert str(fact.org_id) == ids["org_a"]
    assert fact.value == "corporate"
    # The other tenant's selection is untouched and stays attached to its own client.
    other = session.query(ClientFact).filter(
        ClientFact.client_id == UUID(ids["client_b"]), ClientFact.key == "selected_preset_id"
    ).one()
    assert (str(other.org_id), other.value) == (ids["org_b"], "warm")
    session.close()
