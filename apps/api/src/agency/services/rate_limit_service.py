"""Small in-process rate limiter for public MVP endpoints."""
from __future__ import annotations

import time
from collections import deque


class RateLimitError(RuntimeError):
    pass


_BUCKETS: dict[str, deque[float]] = {}


def enforce(key: str, *, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    bucket = _BUCKETS.setdefault(key, deque())
    cutoff = now - window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        raise RateLimitError("rate limit exceeded")
    bucket.append(now)


def reset() -> None:
    _BUCKETS.clear()
