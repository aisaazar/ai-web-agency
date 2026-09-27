"""Password hashing and database-backed session authentication."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.auth_models import AuthSession, Membership, User

_PASSWORDS = PasswordHasher()
SESSION_COOKIE = "agency_session"
SESSION_TTL = timedelta(hours=12)


def hash_password(password: str) -> str:
    return _PASSWORDS.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORDS.verify(password_hash, password)
    except Exception:
        return False


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower().strip()))


def get_membership(session: Session, *, user_id, org_id) -> Membership | None:
    return session.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.org_id == org_id)
    )


def create_session(session: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    record = AuthSession(
        user_id=user.id,
        token_hash=sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + SESSION_TTL,
    )
    session.add(record)
    session.flush()
    return raw_token


def get_user_by_session(session: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    auth_session = session.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
        )
    )
    if auth_session is None:
        return None
    now = datetime.now(timezone.utc)
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        auth_session.revoked_at = now
        return None
    user = session.get(User, auth_session.user_id)
    if user is None or not user.is_active:
        return None
    return user


def revoke_session(session: Session, raw_token: str | None) -> bool:
    if not raw_token:
        return False
    token_hash = sha256(raw_token.encode("utf-8")).hexdigest()
    auth_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if auth_session is None or auth_session.revoked_at is not None:
        return False
    auth_session.revoked_at = datetime.now(timezone.utc)
    return True
