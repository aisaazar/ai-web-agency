import json

from agency.services import turnstile_service


def test_missing_secret_keeps_local_development_compatible(monkeypatch):
    monkeypatch.delenv("AGENCY_TURNSTILE_SECRET", raising=False)
    assert turnstile_service.verify(None) is True


def test_invalid_token_is_rejected(monkeypatch):
    monkeypatch.setenv("AGENCY_TURNSTILE_SECRET", "secret")
    assert turnstile_service.verify("") is False
    assert turnstile_service.verify("x" * 2049) is False


def test_siteverify_success(monkeypatch):
    monkeypatch.setenv("AGENCY_TURNSTILE_SECRET", "secret")

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({"success": True}).encode()

    monkeypatch.setattr(turnstile_service, "urlopen", lambda request, timeout: Response())
    assert turnstile_service.verify("token", "127.0.0.1") is True


def test_siteverify_failure_is_safe(monkeypatch):
    monkeypatch.setenv("AGENCY_TURNSTILE_SECRET", "secret")
    monkeypatch.setattr(turnstile_service, "urlopen", lambda request, timeout: (_ for _ in ()).throw(OSError()))
    assert turnstile_service.verify("token") is False
