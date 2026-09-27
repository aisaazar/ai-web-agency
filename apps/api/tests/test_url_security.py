import pytest

from agency.services.url_security import UnsafeFetchURL, validate_fetch_url


def test_private_ip_is_rejected():
    with pytest.raises(UnsafeFetchURL, match="private"):
        validate_fetch_url("https://127.0.0.1/example")


def test_localhost_is_rejected():
    with pytest.raises(UnsafeFetchURL, match="local"):
        validate_fetch_url("https://localhost/")


def test_dns_private_address_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "agency.services.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("10.0.0.8", 443))],
    )
    with pytest.raises(UnsafeFetchURL, match="resolves to a private"):
        validate_fetch_url("https://example.test/")


def test_public_dns_address_is_allowed(monkeypatch):
    monkeypatch.setattr(
        "agency.services.url_security.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    assert validate_fetch_url("https://example.test/") == "https://example.test/"


def test_http_and_userinfo_are_rejected(monkeypatch):
    with pytest.raises(UnsafeFetchURL):
        validate_fetch_url("http://example.com/")
    with pytest.raises(UnsafeFetchURL):
        validate_fetch_url("https://user:pass@example.com/")
