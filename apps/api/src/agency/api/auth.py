"""Bootstrap and session authentication endpoints."""

import os
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import role_dependency
from agency.api.auth_schemas import (
    AuthResponse,
    AuthUserOut,
    BootstrapRequest,
    LoginRequest,
    MemberCreateRequest,
    MeResponse,
    MembershipOut,
)
from agency.api.dependencies import get_db
from agency.db.auth_models import Membership, User
from agency.db.models import Org
from agency.services.audit_service import record_audit
from agency.services.csrf_service import CSRF_COOKIE, create_csrf_token
from agency.services.auth_service import (
    SESSION_COOKIE,
    create_session,
    get_membership,
    get_user_by_email,
    get_user_by_session,
    hash_password,
    revoke_session,
    verify_password,
)

_LOGIN_LIMIT = 5
_LOGIN_WINDOW_SECONDS = 15 * 60
_login_failures: dict[str, list[float]] = {}


def _login_key(request: Request, email: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{email.lower().strip()}"


def _check_login_limit(request: Request, email: str) -> str:
    key = _login_key(request, email)
    now = time.monotonic()
    recent = [stamp for stamp in _login_failures.get(key, []) if now - stamp < _LOGIN_WINDOW_SECONDS]
    _login_failures[key] = recent
    if len(recent) >= _LOGIN_LIMIT:
        raise HTTPException(status_code=429, detail="too many login attempts", headers={"Retry-After": "900"})
    return key


def _record_login_failure(key: str) -> None:
    _login_failures.setdefault(key, []).append(time.monotonic())


def _clear_login_failures(key: str) -> None:
    _login_failures.pop(key, None)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/auth", tags=["auth"])
    db = get_db(session_factory)
    owner = role_dependency(session_factory, {"owner"})

    def memberships_for(session: Session, user_id) -> list[MembershipOut]:
        rows = session.execute(
            select(Membership, Org)
            .join(Org, Org.id == Membership.org_id)
            .where(Membership.user_id == user_id)
            .order_by(Org.name)
        ).all()
        return [
            MembershipOut(org_id=str(m.org_id), org_name=o.name, role=m.role)
            for m, o in rows
        ]

    def response_for(session: Session, user: User) -> AuthResponse:
        return AuthResponse(
            user=AuthUserOut(id=str(user.id), email=user.email, is_active=user.is_active),
            memberships=memberships_for(session, user.id),
        )

    def set_cookie(response: Response, token: str) -> None:
        secure = os.getenv("AGENCY_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=12 * 60 * 60,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            CSRF_COOKIE,
            create_csrf_token(),
            max_age=12 * 60 * 60,
            httponly=False,
            secure=secure,
            samesite="lax",
            path="/",
        )

    @router.post("/bootstrap", response_model=AuthResponse, status_code=201)
    def bootstrap(
        payload: BootstrapRequest,
        request: Request,
        response: Response,
        session: Session = Depends(db),
    ):
        if session.scalar(select(func.count(User.id))) != 0:
            raise HTTPException(status_code=409, detail="bootstrap already completed")
        email = payload.email.lower().strip()
        if get_user_by_email(session, email) is not None:
            raise HTTPException(status_code=409, detail="user already exists")
        org = Org(name=payload.org_name, slug=payload.org_slug)
        session.add(org)
        session.flush()
        user = User(email=email, password_hash=hash_password(payload.password))
        session.add(user)
        session.flush()
        session.add(Membership(org_id=org.id, user_id=user.id, role="owner"))
        session.flush()
        record_audit(
            session,
            org_id=org.id,
            actor=str(user.id),
            action="auth.bootstrap",
            entity_type="org",
            entity_id=str(org.id),
            after={"email": user.email, "role": "owner"},
            ip=request.client.host if request.client else None,
        )
        set_cookie(response, create_session(session, user))
        return response_for(session, user)

    @router.post("/login", response_model=AuthResponse)
    def login(
        payload: LoginRequest,
        response: Response,
        request: Request,
        session: Session = Depends(db),
    ):
        key = _check_login_limit(request, payload.email)
        user = get_user_by_email(session, payload.email)
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            _record_login_failure(key)
            raise HTTPException(status_code=401, detail="invalid credentials")
        _clear_login_failures(key)
        memberships = memberships_for(session, user.id)
        token = create_session(session, user)
        for membership in memberships:
            record_audit(
                session,
                org_id=membership.org_id,
                actor=str(user.id),
                action="auth.login",
                entity_type="user",
                entity_id=str(user.id),
            )
        set_cookie(response, token)
        return response_for(session, user)

    @router.post("/members", response_model=MembershipOut, status_code=201)
    def add_member(
        org_id: UUID,
        payload: MemberCreateRequest,
        session: Session = Depends(db),
        _owner=Depends(owner),
    ):
        email = payload.email.lower().strip()
        if get_user_by_email(session, email) is not None:
            raise HTTPException(status_code=409, detail="user already exists")
        user = User(email=email, password_hash=hash_password(payload.password))
        session.add(user)
        session.flush()
        membership = Membership(org_id=org_id, user_id=user.id, role=payload.role)
        session.add(membership)
        session.flush()
        org = session.get(Org, org_id)
        record_audit(
            session,
            org_id=org_id,
            actor=str(_owner.user_id),
            action="membership.created",
            entity_type="membership",
            entity_id=str(membership.id),
            after={"email": user.email, "role": membership.role},
        )
        return MembershipOut(
            org_id=str(org_id),
            org_name=org.name,
            role=membership.role,
        )

    @router.get("/me", response_model=MeResponse)
    def me(request: Request, session: Session = Depends(db)):
        user = get_user_by_session(session, request.cookies.get(SESSION_COOKIE))
        if user is None:
            raise HTTPException(status_code=401, detail="authentication required")
        return response_for(session, user)

    @router.post("/logout", status_code=204)
    def logout(request: Request, response: Response, session: Session = Depends(db)):
        token = request.cookies.get(SESSION_COOKIE)
        user = get_user_by_session(session, token)
        if user is not None:
            for membership in memberships_for(session, user.id):
                record_audit(
                    session,
                    org_id=membership.org_id,
                    actor=str(user.id),
                    action="auth.logout",
                    entity_type="user",
                    entity_id=str(user.id),
                )
        revoke_session(session, token)
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.delete_cookie(CSRF_COOKIE, path="/")
        response.status_code = 204
        return response

    return router
