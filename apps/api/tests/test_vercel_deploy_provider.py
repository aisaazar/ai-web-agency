import base64
import json

import pytest

from agency.providers.deploy import BuildBundle
from agency.providers.vercel_deploy import VercelDeploymentError, VercelDeploymentProvider


class _Response:
    def __init__(self, payload=None):
        self.payload = b"" if payload is None else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=None):
        return self.payload if size is None else self.payload[:size]


def _configure(monkeypatch):
    monkeypatch.setenv("VERCEL_TOKEN", "test-token")
    monkeypatch.setenv("VERCEL_PROJECT_ID", "prj_test")
    monkeypatch.delenv("VERCEL_TEAM_ID", raising=False)


def test_vercel_preview_uploads_immutable_bundle(monkeypatch, tmp_path):
    _configure(monkeypatch)
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    (bundle_dir / "index.html").write_text("<h1>hello</h1>", encoding="utf-8")
    (bundle_dir / "assets").mkdir()
    (bundle_dir / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    calls = []

    def fake_urlopen(request, timeout):
        if request.get_method() == "GET":
            return _Response({
                "id": "dpl_123",
                "url": "site-preview.vercel.app",
                "readyState": "READY",
            })
        calls.append((request, json.loads(request.data)))
        return _Response({"id": "dpl_123", "url": "site-preview.vercel.app"})

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    result = VercelDeploymentProvider().create_preview(BuildBundle("a" * 64, bundle_dir))

    assert result.deploy_ref == "dpl_123"
    assert result.url == "https://site-preview.vercel.app"
    assert calls[0][0].full_url.endswith("/v13/deployments")
    payload = calls[0][1]
    assert payload["project"] == "prj_test"
    assert payload["meta"]["ai_web_agency_build_hash"] == "a" * 64
    by_file = {item["file"]: item for item in payload["files"]}
    assert base64.b64decode(by_file["index.html"]["data"]).decode() == "<h1>hello</h1>"


def test_vercel_preview_waits_for_ready(monkeypatch, tmp_path):
    _configure(monkeypatch)
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "index.html").write_text("hello", encoding="utf-8")
    states = iter(["BUILDING", "READY"])

    def fake_urlopen(request, timeout):
        if request.get_method() == "POST":
            return _Response({"id": "dpl_wait", "url": "wait.vercel.app"})
        return _Response({"id": "dpl_wait", "readyState": next(states)})

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    result = VercelDeploymentProvider(ready_poll_seconds=0).create_preview(
        BuildBundle("e" * 64, source)
    )
    assert result.status == "preview_ready"


def test_vercel_preview_rejects_failed_deployment(monkeypatch, tmp_path):
    _configure(monkeypatch)
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "index.html").write_text("hello", encoding="utf-8")

    def fake_urlopen(request, timeout):
        if request.get_method() == "POST":
            return _Response({"id": "dpl_failed", "url": "failed.vercel.app"})
        return _Response({"id": "dpl_failed", "readyState": "ERROR"})

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    with pytest.raises(VercelDeploymentError, match="ended in error state"):
        VercelDeploymentProvider(ready_poll_seconds=0).create_preview(
            BuildBundle("f" * 64, source)
        )


def test_vercel_promote_resolves_preview_url_before_promoting(monkeypatch):
    _configure(monkeypatch)
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        if request.get_method() == "GET":
            return _Response({"id": "dpl_123", "url": "site-preview.vercel.app"})
        return _Response()

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    result = VercelDeploymentProvider().promote("https://site-preview.vercel.app")

    assert result.status == "live"
    assert result.deploy_ref == "dpl_123"
    assert result.url == "https://site-preview.vercel.app"
    assert seen[0].endswith("/v13/deployments/https%3A%2F%2Fsite-preview.vercel.app")
    assert seen[1] == "https://api.vercel.com/v10/projects/prj_test/promote/dpl_123"


def test_vercel_promote_uses_deployment_id_directly(monkeypatch):
    _configure(monkeypatch)
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        return _Response()

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    result = VercelDeploymentProvider().promote("dpl_123")

    assert result.status == "live"
    assert result.deploy_ref == "dpl_123"
    assert seen[0] == "https://api.vercel.com/v10/projects/prj_test/promote/dpl_123"


def test_vercel_rollback_finds_build_metadata_and_promotes(monkeypatch):
    _configure(monkeypatch)
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        if "/v13/deployments?projectId=" in request.full_url:
            return _Response({
                "deployments": [
                    {
                        "id": "dpl_target",
                        "url": "site-target.vercel.app",
                        "meta": {"ai_web_agency_build_hash": "b" * 64},
                    },
                ]
            })
        return _Response()

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    result = VercelDeploymentProvider().rollback("site-1", "b" * 64)

    assert result.deploy_ref == "dpl_target"
    assert result.url == "https://site-target.vercel.app"
    assert any("/v13/deployments?projectId=prj_test" in url for url in seen)
    assert any("/promote/dpl_target" in url for url in seen)


def test_vercel_rollback_rejects_match_without_url(monkeypatch):
    _configure(monkeypatch)

    def fake_urlopen(request, timeout):
        if "/v13/deployments?projectId=" in request.full_url:
            return _Response({
                "deployments": [
                    {"id": "dpl_target", "meta": {"ai_web_agency_build_hash": "b" * 64}},
                ]
            })
        raise AssertionError("promotion must not run without a deployment URL")

    monkeypatch.setattr("agency.providers.vercel_deploy.urlopen", fake_urlopen)
    with pytest.raises(VercelDeploymentError, match="has no url"):
        VercelDeploymentProvider().rollback("site-1", "b" * 64)


def test_vercel_domain_is_pending_until_verified(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(
        "agency.providers.vercel_deploy.urlopen",
        lambda request, timeout: _Response({"name": "clinic.example.de", "verified": False}),
    )
    result = VercelDeploymentProvider().attach_domain("site-1", "Clinic.Example.DE.")
    assert result.status == "pending_verification"
    assert result.fqdn == "clinic.example.de"


def test_vercel_requires_project_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    monkeypatch.delenv("VERCEL_PROJECT_ID", raising=False)
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "index.html").write_text("hello", encoding="utf-8")
    with pytest.raises(VercelDeploymentError, match="VERCEL_PROJECT_ID"):
        VercelDeploymentProvider().create_preview(BuildBundle("c" * 64, source))


def test_vercel_rejects_oversized_bundle(monkeypatch, tmp_path):
    _configure(monkeypatch)
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "index.html").write_text("x" * 100, encoding="utf-8")
    with pytest.raises(VercelDeploymentError, match="exceeds 10 byte limit"):
        VercelDeploymentProvider(max_bundle_bytes=10).create_preview(BuildBundle("d" * 64, source))
