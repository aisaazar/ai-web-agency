from agency.services.site_build_service import _build_environment


def test_static_build_environment_excludes_secret_like_variables(monkeypatch):
    monkeypatch.setenv("EXAMPLE_API_KEY", "synthetic-key")
    monkeypatch.setenv("EXAMPLE_TOKEN", "synthetic-token")
    monkeypatch.setenv("EXAMPLE_PASSWORD", "synthetic-password")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_AGENT_API_URL", "https://api.example.test")
    monkeypatch.setenv("NEXT_PUBLIC_AGENCY_SITE_ID", "site-123")

    env = _build_environment()

    assert "EXAMPLE_API_KEY" not in env
    assert "EXAMPLE_TOKEN" not in env
    assert "EXAMPLE_PASSWORD" not in env
    assert env["NEXT_PUBLIC_AGENCY_AGENT_API_URL"] == "https://api.example.test"
    assert env["NEXT_PUBLIC_AGENCY_SITE_ID"] == "site-123"
    assert env["PRODUCTION_BUILD"] == "1"


def test_build_environment_keeps_runtime_tooling(monkeypatch):
    monkeypatch.setenv("PATH", "synthetic-path")

    env = _build_environment()

    assert env["PATH"] == "synthetic-path"
    assert "PRODUCTION_BUILD" in env
