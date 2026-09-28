"""Cloudflare Turnstile server-side verification boundary."""
from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def configured() -> bool:
    return bool(os.getenv("AGENCY_TURNSTILE_SECRET", "").strip())


def verify(token: str | None, remote_ip: str | None = None) -> bool:
    secret = os.getenv("AGENCY_TURNSTILE_SECRET", "").strip()
    if not secret:
        return True
    if not token or len(token) > 2048:
        return False
    body = {"secret": secret, "response": token}
    if remote_ip:
        body["remoteip"] = remote_ip
    request = Request(
        VERIFY_URL,
        data=urlencode(body).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return bool(payload.get("success"))
    except Exception:
        return False
