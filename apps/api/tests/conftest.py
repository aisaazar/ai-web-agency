import pytest


@pytest.fixture(autouse=True)
def enable_legacy_unauth_for_legacy_tests(monkeypatch):
    """Keep legacy endpoint wiring tests explicit without weakening production defaults."""
    monkeypatch.setenv("AGENCY_ALLOW_LEGACY_UNAUTH", "true")
