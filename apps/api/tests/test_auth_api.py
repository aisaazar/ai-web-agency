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
    assert audit.json()[0]["ip"] == "127.0.0.1"
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


def test_login_rate_limit_blocks_repeated_failures(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'rate-limit.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = []
            for _ in range(6):
                responses.append(
                    await client.post(
                        "/v1/auth/login",
                        json={
                            "email": "rate-limit@example.com",
                            "password": "wrong password",
                        },
                    )
                )
            return responses

    responses = anyio.run(flow)
    assert [response.status_code for response in responses] == [401, 401, 401, 401, 401, 429]
    assert responses[-1].headers["retry-after"] == "900"


def test_login_failure_buckets_are_bounded(tmp_path, monkeypatch):
    from agency.api import auth as auth_api

    auth_api._login_failures.clear()
    monkeypatch.setattr(auth_api, "MAX_LOGIN_BUCKETS", 2)
    app = create_app(f"sqlite:///{tmp_path / 'bounded-login.db'}")

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for email in ("one@example.com", "two@example.com", "three@example.com"):
                response = await client.post(
                    "/v1/auth/login",
                    json={"email": email, "password": "wrong password"},
                )
                assert response.status_code == 401

    try:
        anyio.run(flow)
        assert len(auth_api._login_failures) == 2
        assert "127.0.0.1:one@example.com" not in auth_api._login_failures
        assert "127.0.0.1:three@example.com" in auth_api._login_failures
    finally:
        auth_api._login_failures.clear()
