import anyio
import httpx

from agency.api import create_app


async def _bootstrap_and_add_reviewer(client):
    bootstrap = await client.post(
        "/v1/auth/bootstrap",
        json={
            "org_name": "Role Agency",
            "org_slug": "role-agency",
            "email": "owner@example.com",
            "password": "correct horse battery staple",
        },
    )
    org_id = bootstrap.json()["memberships"][0]["org_id"]
    csrf = client.cookies.get("agency_csrf")
    member = await client.post(
        f"/v1/auth/members?org_id={org_id}",
        headers={"X-CSRF-Token": csrf},
        json={
            "email": "reviewer@example.com",
            "password": "reviewer secure password",
            "role": "reviewer",
        },
    )
    assert member.status_code == 201
    await client.post("/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    login = await client.post(
        "/v1/auth/login",
        json={
            "email": "reviewer@example.com",
            "password": "reviewer secure password",
        },
    )
    assert login.status_code == 200
    return org_id, client.cookies.get("agency_csrf")


def test_reviewer_cannot_run_workflow_mutation(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'roles.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            org_id, csrf = await _bootstrap_and_add_reviewer(client)
            response = await client.post(
                "/v1/intake",
                headers={"X-CSRF-Token": csrf},
                json={
                    "org_id": org_id,
                    "client_name": "Blocked Clinic",
                    "client_slug": "blocked-clinic",
                    "category": "dental",
                    "facts": [],
                },
            )
            overview = await client.get(
                f"/v1/dashboard/overview?org_id={org_id}"
            )
            return response, overview

    blocked, overview = anyio.run(flow)
    assert blocked.status_code == 403
    assert overview.status_code == 200


def test_logged_in_approver_identity_cannot_be_spoofed(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'roles.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            org_id, csrf = await _bootstrap_and_add_reviewer(client)
            response = await client.get(f"/v1/audit?org_id={org_id}")
            return response

    audit = anyio.run(flow)
    assert audit.status_code == 403
