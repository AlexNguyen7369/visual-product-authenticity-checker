"""M13 — Dict cache with TTL.

Goal: read-through caching + TTL semantics BEFORE Redis exists (Phase 5 swaps the dict for
      Redis behind the same interface).
Learn: store (value, expiry); expired == miss; INJECT the clock so tests never sleep().
Maps to: cache/redis_client.py (Phase 5); TTL strategy (24h predictions / 30d confirmed).

See ../src/notes/roadmap.md (M13). Tests: experiments/tests/test_m13_cache.py
"""
import time
from typing import Any, Callable

MISS = object()  # sentinel distinct from any real value (incl. None)


class Cache:
    def __init__(self, now: Callable[[], float] = time.time):
        self._now = now                 # injectable clock -> deterministic, fast tests
        self._store: dict[str, tuple[Any, float]] = {}

    def set(self, key: str, value: Any, ttl: float) -> None:
        """Store value with an expiry of now + ttl seconds."""
        # TODO: self._store[key] = (value, self._now() + ttl)
        raise NotImplementedError

    def get(self, key: str) -> Any:
        """Return the value, or MISS if absent or expired. Expired entries should be a miss."""
        # TODO: look up; if absent -> MISS; if self._now() >= expiry -> MISS; else value
        # (Watch the boundary: is exactly-at-expiry a hit or a miss? Pick one and test it.)
        raise NotImplementedError


def main() -> None:
    c = Cache()
    c.set("k", "v", ttl=60)
    print("immediate get:", c.get("k"))
    print("unknown key  :", c.get("missing") is MISS)


if __name__ == "__main__":
    main()
