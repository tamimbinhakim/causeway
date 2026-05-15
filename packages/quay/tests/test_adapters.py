"""Reference adapter tests."""

from __future__ import annotations

import asyncio

import pytest

from quay.adapters import (
    CookieStore,
    LocalStorage,
    MemoryBus,
    MemoryKV,
    MemoryLimiter,
    NullScanner,
    NullSink,
    StaticFlags,
    StdoutLogSink,
)

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------


async def test_local_storage_put_get_delete() -> None:
    s = LocalStorage()
    await s.put("k", b"hello")
    assert await s.get("k") == b"hello"
    await s.delete("k")
    with pytest.raises(FileNotFoundError):
        await s.get("k")


async def test_local_storage_list_filters_by_prefix() -> None:
    s = LocalStorage()
    await s.put("a/1", b"x")
    await s.put("a/2", b"y")
    await s.put("b/1", b"z")
    keys = [k async for k in s.list("a/")]
    assert keys == ["a/1", "a/2"]


async def test_local_storage_signed_url_round_trips_key() -> None:
    s = LocalStorage()
    assert (await s.signed_url("foo/bar.txt")).endswith("foo/bar.txt")


# ---------------------------------------------------------------------------
# KV
# ---------------------------------------------------------------------------


async def test_kv_basic_roundtrip() -> None:
    kv = MemoryKV()
    assert await kv.get("missing") is None
    await kv.set("k", b"v")
    assert await kv.get("k") == b"v"
    await kv.delete("k")
    assert await kv.get("k") is None


async def test_kv_incr() -> None:
    kv = MemoryKV()
    assert await kv.incr("counter") == 1
    assert await kv.incr("counter", by=5) == 6


async def test_kv_ttl_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    kv = MemoryKV()

    fake_now = [100.0]

    def now() -> float:
        return fake_now[0]

    monkeypatch.setattr("quay.adapters.time.monotonic", now)

    await kv.set("k", b"v", ttl=10)
    assert await kv.get("k") == b"v"
    fake_now[0] = 200.0  # past TTL
    assert await kv.get("k") is None


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def test_cookie_store_rotate_moves_data() -> None:
    s = CookieStore()
    await s.write("old", {"user": "ada"})
    new = await s.rotate("old")
    assert new != "old"
    assert await s.read("old") is None
    assert await s.read(new) == {"user": "ada"}


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


async def test_memory_limiter_blocks_after_capacity() -> None:
    lim = MemoryLimiter(capacity=3, refill_per_sec=0)
    assert await lim.acquire("user") is True
    assert await lim.acquire("user") is True
    assert await lim.acquire("user") is True
    assert await lim.acquire("user") is False  # bucket empty
    await lim.reset("user")
    assert await lim.acquire("user") is True


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


async def test_static_flags_default_off() -> None:
    f = StaticFlags()
    assert await f.is_on("new_ui") is False


async def test_static_flags_seeded_from_settings() -> None:
    f = StaticFlags()

    class _Settings:
        feature_flags = {"new_ui": True, "beta": False}

    await f.startup(_Settings())
    assert await f.is_on("new_ui") is True
    assert await f.is_on("beta") is False
    assert await f.is_on("missing") is False


# ---------------------------------------------------------------------------
# Metrics + logs (no observable side effects, just smoke)
# ---------------------------------------------------------------------------


async def test_null_sink_swallows() -> None:
    s = NullSink()
    s.counter("hits")
    s.gauge("queue.depth", 5.0)
    s.histogram("latency_ms", 1.2)
    async with s.timer("op"):
        pass


def test_stdout_log_sink_emits() -> None:
    StdoutLogSink().emit({"event": "started"})


# ---------------------------------------------------------------------------
# Pub/sub
# ---------------------------------------------------------------------------


async def test_pubsub_fans_out_to_every_subscriber() -> None:
    bus = MemoryBus()
    a_seen: list[bytes] = []
    b_seen: list[bytes] = []

    async def a(payload: bytes) -> None:
        a_seen.append(payload)

    async def b(payload: bytes) -> None:
        b_seen.append(payload)

    await bus.subscribe("evt", a)
    await bus.subscribe("evt", b)
    await bus.publish("evt", b"hi")
    # Yield once for tasks fan-out to complete.
    await asyncio.sleep(0)
    assert a_seen == [b"hi"]
    assert b_seen == [b"hi"]


# ---------------------------------------------------------------------------
# Blob scanner
# ---------------------------------------------------------------------------


async def test_null_scanner_drains_and_says_clean() -> None:
    async def chunks():
        yield b"abc"
        yield b"def"

    assert await NullScanner().scan(chunks()) is True
