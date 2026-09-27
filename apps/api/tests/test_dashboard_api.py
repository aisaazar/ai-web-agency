import anyio
import httpx

from agency.api import create_app


def test_dashboard_returns_empty_real_api_shape_for_empty_org(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'dashboard.db'}")

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/v1/dashboard")

    response = anyio.run(request)

    assert response.status_code == 200
    assert response.json() == {
        "clients": [],
        "artifacts": [],
        "deployments": [],
        "leads": [],
    }
