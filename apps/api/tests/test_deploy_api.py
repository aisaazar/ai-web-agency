from types import SimpleNamespace
from uuid import uuid4

import anyio
import httpx

from agency.api import create_app


def _post(app, path, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(path, json=payload)
    return anyio.run(request)


def test_rollback_endpoint_wires_service_result(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    expected_build = "4" * 64
    expected_deploy = uuid4()
    expected_version = uuid4()

    import agency.api.deploy as deploy_api
    monkeypatch.setattr(
        deploy_api,
        "rollback_site",
        lambda session, **kwargs: SimpleNamespace(
            id=expected_deploy,
            site_version_id=expected_version,
            provider="local_static",
            status="live",
            url=f"file:///deploy/{expected_build}",
        ),
    )
    app = create_app(database_url)
    response = _post(app, "/v1/deploys/rollback", {
        "org_id": str(uuid4()),
        "client_id": str(uuid4()),
        "build_hash": expected_build,
    })

    assert response.status_code == 201
    assert response.json()["deploy_id"] == str(expected_deploy)
    assert response.json()["site_version_id"] == str(expected_version)
    assert response.json()["build_hash"] == expected_build
    assert response.json()["state"] == "LIVE"
