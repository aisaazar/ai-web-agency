from agency.services import rate_limit_service
from agency.services.rate_limit_service import RateLimitError, enforce, reset


def test_rate_limit_blocks_after_limit():
    reset()
    for _ in range(3):
        enforce("test", limit=3, window_seconds=60)
    try:
        enforce("test", limit=3, window_seconds=60)
    except RateLimitError:
        pass
    else:
        raise AssertionError("expected rate limit")


def test_rate_limit_keys_are_isolated():
    reset()
    enforce("one", limit=1, window_seconds=60)
    enforce("two", limit=1, window_seconds=60)
    try:
        enforce("one", limit=1, window_seconds=60)
    except RateLimitError:
        pass
    else:
        raise AssertionError("expected isolated bucket to block")


def test_rate_limit_bucket_count_is_bounded(monkeypatch):
    monkeypatch.setattr(rate_limit_service, "MAX_BUCKETS", 2)
    reset()
    enforce("one", limit=1, window_seconds=60)
    enforce("two", limit=1, window_seconds=60)
    enforce("three", limit=1, window_seconds=60)

    assert len(rate_limit_service._BUCKETS) == 2
    assert "three" in rate_limit_service._BUCKETS
    reset()
