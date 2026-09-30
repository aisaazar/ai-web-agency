"""Small in-process rate limiter for public MVP endpoints."""
from __future__ import annotations

import time
from collections import OrderedDict, deque
from threading import Lock


class RateLimitError(RuntimeError):
    pass


# Public endpoints can receive attacker-controlled identifiers. Keep the in-process
# limiter bounded so unique keys cannot grow memory without limit.
MAX_BUCKETS = 4096
_BUCKETS: OrderedDict[str, deque[float]] = OrderedDict()
_LOCK = Lock()


def enforce(key: str, *, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    cutoff = now - window_seconds
    with _LOCK:
        bucket = _BUCKETS.get(key)
        if bucket is None:
            if len(_BUCKETS) >= MAX_BUCKETS:
                _BUCKETS.popitem(last=False)
            bucket = deque()
            _BUCKETS[key] = bucket
        else:
            _BUCKETS.move_to_end(key)
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise RateLimitError("rate limit exceeded")
        bucket.append(now)


def reset() -> None:
    with _LOCK:
        _BUCKETS.clear()
