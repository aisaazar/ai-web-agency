"""Double-submit CSRF token helpers for browser session protection."""

import secrets

CSRF_COOKIE = "agency_csrf"
CSRF_HEADER = "x-csrf-token"


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def valid_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    return secrets.compare_digest(cookie_token, header_token)
