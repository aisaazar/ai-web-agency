import anyio
import httpx

from agency.api import create_app
from agency.db.models import Org
from agency.db.session import create_session_factory


def test_dashboard_returns_empty_real_api_shape_for_empty_org(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'dashboard.db'}"
    app = create_app(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Dashboard Agency", slug="dashboard-agency")
    session.add(org)
    session.commit()
    session.close()

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(f"/v1/dashboard/overview?org_id={org.id}")

    response = anyio.run(request)

    assert response.status_code == 200
    assert response.json() == {
        "org_id": str(org.id),
        "counts": {
            "clients": 0,
            "artifacts": 0,
            "deployments": 0,
            "new_leads": 0,
        },
        "clients": [],
        "artifacts": [],
        "deployments": [],
        "leads": [],
    }
