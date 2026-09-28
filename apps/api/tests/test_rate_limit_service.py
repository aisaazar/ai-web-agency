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
