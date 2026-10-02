import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import anyio
import httpx
import pytest

from agency.api import create_app
from agency.db import create_all, create_session_factory
from agency.db.models import Artifact, BuildValidation, Client, Org, SiteVersion
from agency.db.workflow_models import PipelineRun
from agency.providers.deploy import BUILD_COMPLETE_MARKER


FIXTURE = Path(__file__).resolve().parents[3] / "sites" / "_template-base" / "content.dental-clinic.json"
REPO_ROOT = Path(__file__).resolve().parents[3]

def test_run_uses_system_npm_cli_on_windows(monkeypatch, tmp_path):
    import agency.services.site_build_service as build_module

    captured = {}
    node_dir = tmp_path / "ProgramFiles" / "nodejs"
    node_dir.mkdir(parents=True)
    system_npm = node_dir / "npm.cmd"
    node_exe = node_dir / "node.exe"
    npm_cli = node_dir / "node_modules" / "npm" / "bin" / "npm-cli.js"
    system_npm.write_text("@echo off", encoding="utf-8")
    node_exe.write_text("synthetic", encoding="utf-8")
    npm_cli.parent.mkdir(parents=True)
    npm_cli.write_text("synthetic", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr(build_module.subprocess, "run", fake_run)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "ProgramFiles"))
    monkeypatch.setattr(
        build_module.shutil,
        "which",
        lambda name, path=None: r"C:\Users\Admin\.cline\worktrees\polluted\node_modules\.bin\npm.cmd",
    )

    passed, detail = build_module._run(["npm", "--version"], cwd=tmp_path, env={"PATH": "synthetic"})

    assert passed
    assert detail == "ok"
    assert captured["command"] == [str(node_exe), str(npm_cli), "--version"]
    assert captured["kwargs"]["encoding"] == "utf-8"
    assert captured["kwargs"]["errors"] == "replace"


def test_template_build_lock_is_process_exclusive(monkeypatch, tmp_path):
    import agency.services.site_build_service as build_module

    lock_path = tmp_path / "template-build.lock"
    monkeypatch.setattr(build_module, "BUILD_LOCK_PATH", lock_path)
    child_script = """
import sys
import time
from pathlib import Path
from agency.services import site_build_service as build

build.BUILD_LOCK_PATH = Path(sys.argv[1])
with build._template_build_lock():
    print("locked", flush=True)
    time.sleep(0.75)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", child_script, str(lock_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert child.stdout is not None
    assert child.stdout.readline().strip() == "locked"

    started = time.monotonic()
    with build_module._template_build_lock():
        waited = time.monotonic() - started

    stdout, stderr = child.communicate(timeout=5)
    assert child.returncode == 0, stderr or stdout
    assert waited >= 0.5



def _fake_persist_build_bundle(build_hash):
    destination = REPO_ROOT / ".artifacts" / "builds" / build_hash
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text("<!doctype html><html><body>test</body></html>", encoding="utf-8")
    (destination / BUILD_COMPLETE_MARKER).write_text("ok\n", encoding="utf-8")
    return destination


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)

    return anyio.run(request)


def _seed(database_url, preset_id="health"):
    create_all(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    facts = Artifact(
        org_id=org.id,
        artifact_type="business_facts",
        schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []},
    )
    session.add(facts)
    session.flush()

    content_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    content = Artifact(
        org_id=org.id,
        artifact_type="content_model",
        schema_version="1.0.0",
        payload_json=content_data,
        input_artifact_id=facts.id,
    )
    design = Artifact(
        org_id=org.id,
        artifact_type="design_plan",
        schema_version="1.0.0",
        payload_json={
            "client_id": str(client.id),
            "template_id": "_template-base",
            "template_version": "1.0.0",
            "design_preset_id": preset_id,
        },
    )
    session.add_all([content, design, PipelineRun(
        org_id=org.id,
        client_id=client.id,
        state="DESIGN_APPROVED",
    )])
    session.commit()
    session.close()
    return org, client, content.id, design.id


def test_site_build_endpoint_reaches_preview_ready(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url)

    def fake_run(command, *, cwd, env):
        return True, f"mocked: {' '.join(command)}"

    import agency.services.site_build_service as build_module
    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    app = create_app(database_url)
    response = _post(app, "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["site_version_id"])
    assert len(body["build_hash"]) == 64
    assert body["state"] == "PREVIEW_READY"

    factory = create_session_factory(database_url)
    session = factory()
    version = session.get(SiteVersion, UUID(body["site_version_id"]))
    validations = session.query(BuildValidation).filter(
        BuildValidation.site_version_id == version.id
    ).all()

    assert version is not None
    assert len(validations) == 11
    assert all(item.passed for item in validations)
    assert {item.check_name for item in validations} == {
        "content_schema", "facts_provenance", "claims_policy",
        "required_legal_pages", "typecheck", "next_build",
        "linkcheck", "a11y_budget", "playwright_smoke",
        "seo_manifest", "perf_budget",
    }
    session.close()


@pytest.mark.parametrize("preset_id", ["health", "corporate", "warm"])
def test_site_build_injects_per_client_public_runtime_ids(tmp_path, monkeypatch, preset_id):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url, preset_id)
    captured: dict[tuple[str, ...], dict[str, str]] = {}

    import agency.services.site_build_service as build_module

    def fake_run(command, *, cwd, env):
        captured[tuple(command)] = {
            "client_id": env["NEXT_PUBLIC_AGENCY_CLIENT_ID"],
            "site_id": env["NEXT_PUBLIC_AGENCY_SITE_ID"],
            "design_preset": env["DESIGN_PRESET_ID"],
            "lead_api": env["NEXT_PUBLIC_AGENCY_LEAD_API_URL"],
            "agent_api": env["NEXT_PUBLIC_AGENCY_AGENT_API_URL"],
        }
        return True, f"mocked: {' '.join(command)}"

    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_LEAD_API_URL", "https://api.example.test/")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_AGENT_API_URL", "")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_CLIENT_ID", "wrong-client")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_SITE_ID", "wrong-site")
    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    app = create_app(database_url)
    response = _post(app, "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })

    assert response.status_code == 201
    build_env = captured[("npm", "run", "build:site")]
    assert build_env["client_id"] == str(client.id)
    assert build_env["design_preset"] == preset_id
    assert build_env["lead_api"] == "https://api.example.test"
    assert build_env["agent_api"] == "https://api.example.test"
    assert UUID(build_env["site_id"])


def test_site_build_restores_template_tokens_after_preset_build(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url, "corporate")

    import agency.services.site_build_service as build_module
    generated_tokens_path = build_module.TEMPLATE_ROOT / "src" / "styles" / "design-tokens.generated.css"
    original = generated_tokens_path.read_bytes()

    def fake_run(command, *, cwd, env):
        if command == ["npm", "run", "build:site"]:
            generated_tokens_path.write_text("temporary corporate tokens", encoding="utf-8")
        return True, f"mocked: {' '.join(command)}"

    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    response = _post(create_app(database_url), "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })

    assert response.status_code == 201
    assert generated_tokens_path.read_bytes() == original


def test_site_build_preserves_separate_public_runtime_endpoints(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url)
    captured: dict[str, str] = {}

    import agency.services.site_build_service as build_module

    def fake_run(command, *, cwd, env):
        captured.update({
            "lead_api": env["NEXT_PUBLIC_AGENCY_LEAD_API_URL"],
            "agent_api": env["NEXT_PUBLIC_AGENCY_AGENT_API_URL"],
        })
        return True, f"mocked: {' '.join(command)}"

    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_LEAD_API_URL", "https://leads.example.test/")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_AGENT_API_URL", "https://agent.example.test/")
    monkeypatch.setattr(build_module, "_run", fake_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    response = _post(create_app(database_url), "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })

    assert response.status_code == 201
    assert captured == {
        "lead_api": "https://leads.example.test",
        "agent_api": "https://agent.example.test",
    }


def test_publish_approval_binds_to_exact_build_artifact(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url)

    import agency.services.site_build_service as build_module
    monkeypatch.setattr(
        build_module,
        "_run",
        lambda command, *, cwd, env: (True, f"mocked: {' '.join(command)}"),
    )
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    app = create_app(database_url)
    built = _post(app, "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })
    assert built.status_code == 201

    session = create_session_factory(database_url)()
    build_artifact = session.query(Artifact).filter(
        Artifact.org_id == org.id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == built.json()["build_hash"],
    ).one()
    session.close()

    preview = _post(app, "/v1/deploys/preview", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "site_version_id": str(built.json()["site_version_id"]),
    })
    assert preview.status_code == 201

    approved = _post(app, "/v1/publish/approve", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "build_artifact_id": str(build_artifact.id),
        "approved_by": "owner@example.com",
    })
    assert approved.status_code == 200
    assert approved.json()["state"] == "PREVIEW_APPROVED"
    assert approved.json()["build_hash"] == built.json()["build_hash"]


def test_publish_deploy_requires_exact_build_and_reaches_live(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url)

    import agency.services.site_build_service as build_module
    monkeypatch.setattr(
        build_module,
        "_run",
        lambda command, *, cwd, env: (True, f"mocked: {' '.join(command)}"),
    )
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    app = create_app(database_url)
    built = _post(app, "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })
    assert built.status_code == 201

    session = create_session_factory(database_url)()
    build_artifact = session.query(Artifact).filter(
        Artifact.org_id == org.id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == built.json()["build_hash"],
    ).one()
    session.close()

    rejected_approval = _post(app, "/v1/publish/approve", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "build_artifact_id": str(build_artifact.id),
        "approved_by": "owner@example.com",
    })
    assert rejected_approval.status_code == 400
    assert "preview deployment" in rejected_approval.json()["detail"]

    preview = _post(app, "/v1/deploys/preview", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "site_version_id": str(built.json()["site_version_id"]),
    })
    assert preview.status_code == 201
    assert preview.json()["state"] == "PREVIEW_READY"

    preview_again = _post(app, "/v1/deploys/preview", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "site_version_id": str(built.json()["site_version_id"]),
    })
    assert preview_again.status_code == 201
    assert preview_again.json()["deploy_id"] == preview.json()["deploy_id"]

    approved = _post(app, "/v1/publish/approve", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "build_artifact_id": str(build_artifact.id),
        "approved_by": "owner@example.com",
    })
    assert approved.status_code == 200

    deployed = _post(app, "/v1/deploys/publish", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "site_version_id": str(built.json()["site_version_id"]),
    })
    assert deployed.status_code == 201
    assert deployed.json()["state"] == "LIVE"
    assert deployed.json()["status"] == "live"


def test_site_build_failure_persists_diagnostics(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    org, client, content_id, design_id = _seed(database_url)

    import agency.services.site_build_service as build_module

    def failing_run(command, *, cwd, env):
        return False, f"mocked failure: {' '.join(command)}"

    monkeypatch.setattr(build_module, "_run", failing_run)
    monkeypatch.setattr(build_module, "_persist_build_bundle", _fake_persist_build_bundle)

    app = create_app(database_url)
    response = _post(app, "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })

    assert response.status_code == 400
    assert "build validation failed" in response.json()["detail"]

    session = create_session_factory(database_url)()
    pipeline = session.query(PipelineRun).filter(
        PipelineRun.org_id == org.id,
        PipelineRun.client_id == client.id,
    ).order_by(PipelineRun.created_at.desc()).first()
    validations = session.query(BuildValidation).all()

    assert pipeline is not None
    assert pipeline.state == "BUILD_FAILED"
    assert len(validations) == 11
    assert any(not item.passed for item in validations)
    failed_version_count = session.query(SiteVersion).filter(
        SiteVersion.org_id == org.id
    ).count()
    assert failed_version_count == 1
    session.close()

    monkeypatch.setattr(
        build_module,
        "_run",
        lambda command, *, cwd, env: (True, f"mocked: {' '.join(command)}"),
    )
    retry = _post(app, "/v1/builds/site", {
        "org_id": str(org.id),
        "client_id": str(client.id),
        "content_artifact_id": str(content_id),
        "design_artifact_id": str(design_id),
    })

    assert retry.status_code == 201
    assert retry.json()["state"] == "PREVIEW_READY"

    session = create_session_factory(database_url)()
    versions = session.query(SiteVersion).filter(
        SiteVersion.org_id == org.id
    ).all()
    assert len(versions) == 1
    assert versions[0].build_hash == retry.json()["build_hash"]
    assert session.query(BuildValidation).filter(
        BuildValidation.site_version_id == versions[0].id
    ).count() == 11
    session.close()


def test_build_runner_decodes_utf8_output_independent_of_machine_locale(tmp_path):
    """The site build emits UTF-8, so the runner must not depend on the console codepage.

    On a cp1252 machine the Next.js route table can contain multi-byte box-drawing characters;
    this regression keeps the failure diagnosable instead of surfacing as an opaque HTTP 500.
    """
    import os
    import sys

    from agency.services.site_build_service import _run

    marker = "\u2500\u00e4\u00f6\u00fc preview-art-direction"
    ok, detail = _run(
        [sys.executable, "-c", f"print({marker!r})"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert ok is True
    assert marker in detail
