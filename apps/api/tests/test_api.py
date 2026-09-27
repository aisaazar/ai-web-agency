import anyio
import httpx

from agency.api import create_app


def test_health_endpoint():
    app = create_app("sqlite:///:memory:")

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = anyio.run(request)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
