"""Tests for M13. Red until you implement Cache.set/get.

Note the fake `clock` fixture (from conftest.py): we advance time instead of sleeping, so the
TTL tests are instant and deterministic.
"""
from m13_cache_ttl import Cache, MISS


def test_set_then_get_hits(clock):
    c = Cache(now=clock)
    c.set("k", "v", ttl=60)
    assert c.get("k") == "v"


def test_unknown_key_misses(clock):
    c = Cache(now=clock)
    assert c.get("nope") is MISS


def test_expired_entry_misses(clock):
    c = Cache(now=clock)
    c.set("k", "v", ttl=10)
    clock.advance(11)               # no real sleep — just move the clock past expiry
    assert c.get("k") is MISS


def test_not_yet_expired_hits(clock):
    c = Cache(now=clock)
    c.set("k", "v", ttl=10)
    clock.advance(9)
    assert c.get("k") == "v"
