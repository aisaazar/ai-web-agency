import anyio
import httpx

from agency.api import create_app
from agency.db.models import Client, Org
from agency.db.session import create_session_factory


async def _bootstrap(client):
    response = await client.post(
        "/v1/auth/bootstrap",
        json={
            "org_name": "Tenant A",
            "org_slug": "tenant-a",
            "email": "owner-a@example.com",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201
    return response.json()["memberships"][0]["org_id"]


def test_authenticated_owner_cannot_read_another_org(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'tenant.db'}"
    app = create_app(database_url)

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            org_a = await _bootstrap(client)
            session = create_session_factory(database_url)()
            try:
                org_b = Org(name="Tenant B", slug="tenant-b")
                session.add(org_b)
                session.flush()
                session.add(Client(
                    org_id=org_b.id,
                    name="Tenant B Clinic",
                    slug="tenant-b-clinic",
                    category="dental",
                ))
                session.commit()
                dashboard = await client.get(f"/v1/dashboard/overview?org_id={org_b.id}")
                leads = await client.get(f"/v1/leads?org_id={org_b.id}")
                own_dashboard = await client.get(f"/v1/dashboard/overview?org_id={org_a}")
                return dashboard, leads, own_dashboard
            finally:
                session.close()

    dashboard, leads, own_dashboard = anyio.run(flow)
    assert dashboard.status_code == 403
    assert leads.status_code == 403
    assert own_dashboard.status_code == 200
