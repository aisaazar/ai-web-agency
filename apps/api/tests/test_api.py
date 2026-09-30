import anyio
import httpx
import pytest

from agency.api import create_app


def test_database_url_environment_is_used(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'configured.db'}"
    monkeypatch.setenv("AGENCY_DATABASE_URL", database_url)
    create_app()
    assert (tmp_path / "configured.db").exists()


def test_health_endpoint():
    app = create_app("sqlite:///:memory:")

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = anyio.run(request)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_production_rejects_insecure_origin(monkeypatch):
    monkeypatch.setenv("AGENCY_ENV", "production")
    monkeypatch.setenv("AGENCY_ALLOWED_ORIGINS", "http://client.example")
    monkeypatch.setenv("AGENCY_COOKIE_SECURE", "true")

    with pytest.raises(RuntimeError, match="HTTPS AGENCY_ALLOWED_ORIGINS"):
        create_app("sqlite:///:memory:")


def test_production_requires_secure_cookie(monkeypatch):
    monkeypatch.setenv("AGENCY_ENV", "production")
    monkeypatch.setenv("AGENCY_ALLOWED_ORIGINS", "https://client.example")
    monkeypatch.setenv("AGENCY_COOKIE_SECURE", "false")

    with pytest.raises(RuntimeError, match="AGENCY_COOKIE_SECURE=true"):
        create_app("sqlite:///:memory:")


def test_production_requires_turnstile_secret(monkeypatch):
    monkeypatch.setenv("AGENCY_ENV", "production")
    monkeypatch.setenv("AGENCY_ALLOWED_ORIGINS", "https://client.example")
    monkeypatch.setenv("AGENCY_COOKIE_SECURE", "true")
    monkeypatch.delenv("AGENCY_TURNSTILE_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="AGENCY_TURNSTILE_SECRET"):
        create_app("sqlite:///:memory:")


def test_cors_allows_configured_site_origin(monkeypatch):
    monkeypatch.setenv("AGENCY_ALLOWED_ORIGINS", "https://client.example")
    app = create_app("sqlite:///:memory:")

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.options(
                "/health",
                headers={
                    "Origin": "https://client.example",
                    "Access-Control-Request-Method": "GET",
                },
            )

    response = anyio.run(request)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://client.example"
