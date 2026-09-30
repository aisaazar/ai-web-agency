"""HTTP authentication dependencies for session-backed access."""

import os
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from agency.api.dependencies import get_db
from agency.db.auth_models import Membership, User
from agency.services.auth_service import get_membership, get_user_by_session


def current_user_dependency(session_factory: sessionmaker[Session]):
    db = get_db(session_factory)

    def dependency(
        request: Request,
        session: Session = Depends(db),
    ) -> User:
        user = get_user_by_session(session, request.cookies.get("agency_session"))
        if user is None:
            raise HTTPException(status_code=401, detail="authentication required")
        return user

    return dependency


def role_dependency(session_factory: sessionmaker[Session], roles: set[str]):
    db = get_db(session_factory)

    def dependency(
        request: Request,
        org_id: UUID,
        session: Session = Depends(db),
    ) -> Membership:
        user = get_user_by_session(session, request.cookies.get("agency_session"))
        if user is None:
            raise HTTPException(status_code=401, detail="authentication required")
        membership = get_membership(session, user_id=user.id, org_id=org_id)
        if membership is None or membership.role not in roles:
            raise HTTPException(status_code=403, detail="insufficient role")
        return membership

    return dependency

def require_role_or_legacy(
    session: Session,
    request: Request,
    *,
    org_id: UUID,
    roles: set[str],
):
    """Authorize an org mutation, preserving uninitialized legacy/test orgs."""
    user = get_user_by_session(session, request.cookies.get("agency_session"))
    if user is None:
        user_count = session.scalar(select(func.count(User.id)))
        membership_count = session.scalar(select(func.count(Membership.id)))
        legacy_enabled = os.getenv("AGENCY_ALLOW_LEGACY_UNAUTH", "").strip().lower() in {"1", "true", "yes"}
        if legacy_enabled and user_count == 0 and membership_count == 0:
            return None
        raise HTTPException(status_code=401, detail="authentication required")
    membership = get_membership(session, user_id=user.id, org_id=org_id)
    if membership is None or membership.role not in roles:
        raise HTTPException(status_code=403, detail="insufficient role")
    return membership
