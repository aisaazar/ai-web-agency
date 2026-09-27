import anyio
import httpx

from agency.api import create_app


def test_bootstrap_login_me_logout_and_owner_audit(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'auth.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            bootstrap = await client.post(
                "/v1/auth/bootstrap",
                json={
                    "org_name": "Demo Agency",
                    "org_slug": "demo-agency",
                    "email": "owner@example.com",
                    "password": "correct horse battery staple",
                },
            )
            me = await client.get("/v1/auth/me")
            org_id = bootstrap.json()["memberships"][0]["org_id"]
            csrf = client.cookies.get("agency_csrf")
            audit = await client.get(f"/v1/audit?org_id={org_id}")
            member = await client.post(
                f"/v1/auth/members?org_id={org_id}",
                headers={"X-CSRF-Token": csrf},
                json={
                    "email": "reviewer@example.com",
                    "password": "reviewer secure password",
                    "role": "reviewer",
                },
            )
            logout = await client.post("/v1/auth/logout", headers={"X-CSRF-Token": csrf})
            after_logout = await client.get("/v1/auth/me")
            login = await client.post(
                "/v1/auth/login",
                json={
                    "email": "owner@example.com",
                    "password": "correct horse battery staple",
                },
            )
            reviewer_login = await client.post(
                "/v1/auth/login",
                json={
                    "email": "reviewer@example.com",
                    "password": "reviewer secure password",
                },
            )
            reviewer_audit = await client.get(f"/v1/audit?org_id={org_id}")
            bad_login = await client.post(
                "/v1/auth/login",
                json={"email": "owner@example.com", "password": "wrong password"},
            )
            return bootstrap, me, audit, member, logout, after_logout, login, reviewer_login, reviewer_audit, bad_login

    bootstrap, me, audit, member, logout, after_logout, login, reviewer_login, reviewer_audit, bad_login = anyio.run(flow)

    assert bootstrap.status_code == 201
    assert "HttpOnly" in bootstrap.headers["set-cookie"]
    assert "SameSite=lax" in bootstrap.headers["set-cookie"]
    assert bootstrap.cookies.get("agency_csrf")
    assert bootstrap.json()["memberships"][0]["role"] == "owner"
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "owner@example.com"
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "auth.bootstrap"
    assert member.status_code == 201
    assert member.json()["role"] == "reviewer"
    assert reviewer_login.status_code == 200
    assert reviewer_audit.status_code == 403
    assert logout.status_code == 204
    assert after_logout.status_code == 401
    assert login.status_code == 200
    assert bad_login.status_code == 401


def test_bootstrap_only_allowed_once(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'auth.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "org_name": "Demo Agency",
                "org_slug": "demo-agency",
                "email": "owner@example.com",
                "password": "correct horse battery staple",
            }
            first = await client.post("/v1/auth/bootstrap", json=payload)
            second = await client.post(
                "/v1/auth/bootstrap",
                json={**payload, "email": "other@example.com"},
            )
            return first, second

    first, second = anyio.run(flow)
    assert first.status_code == 201
    assert second.status_code == 409


def test_mutating_authenticated_request_requires_csrf(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'csrf.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            bootstrap = await client.post(
                "/v1/auth/bootstrap",
                json={
                    "org_name": "CSRF Agency",
                    "org_slug": "csrf-agency",
                    "email": "owner@example.com",
                    "password": "correct horse battery staple",
                },
            )
            org_id = bootstrap.json()["memberships"][0]["org_id"]
            blocked = await client.post(
                f"/v1/auth/members?org_id={org_id}",
                json={
                    "email": "reviewer@example.com",
                    "password": "reviewer secure password",
                    "role": "reviewer",
                },
            )
            return blocked

    blocked = anyio.run(flow)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "CSRF token required"
