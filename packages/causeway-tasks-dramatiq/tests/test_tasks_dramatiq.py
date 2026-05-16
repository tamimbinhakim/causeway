from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone
from typing import Any

import dramatiq
import pytest
from dramatiq.brokers.stub import StubBroker
from pydantic import SecretStr

import causeway.plugins as plugin_registry
from causeway.tasks import TaskRef
from causeway_tasks_dramatiq import DramatiqAdapter, plugin


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    plugin_registry.clear()


@pytest.fixture
def stub_broker(monkeypatch: pytest.MonkeyPatch) -> StubBroker:
    """Swap RedisBroker for StubBroker so startup() doesn't dial Redis."""
    captured: dict[str, StubBroker] = {}

    class _StubFactory(StubBroker):
        def __init__(self, *, url: str | None = None) -> None:
            super().__init__()
            self.url = url
            captured["broker"] = self

    monkeypatch.setattr("causeway_tasks_dramatiq.RedisBroker", _StubFactory)
    return captured  # type: ignore[return-value]


def _make_ref(name: str, called: list[tuple[Any, ...]]) -> TaskRef:
    async def fn(*args: Any, **kwargs: Any) -> None:
        called.append((args, kwargs))

    fn.__module__ = "tests"
    fn.__name__ = name
    return TaskRef(module="tests", name=name, fn=fn)


async def test_lifecycle_starts_broker(stub_broker: dict[str, StubBroker]) -> None:
    adapter = DramatiqAdapter(broker_url="redis://x")
    assert await adapter.ready() is False
    await adapter.startup(None)
    try:
        assert await adapter.ready() is True
        # set_adapter wired us up as the active task adapter.
        from causeway.tasks import _active_adapter  # type: ignore[attr-defined]

        assert _active_adapter() is adapter
    finally:
        await adapter.shutdown()
    assert await adapter.ready() is False


async def test_enqueue_pushes_to_broker(stub_broker: dict[str, StubBroker]) -> None:
    called: list[tuple[Any, ...]] = []
    ref = _make_ref("greet", called)

    adapter = DramatiqAdapter(broker_url="redis://x")
    await adapter.startup(None)
    try:
        msg_id = await adapter.enqueue(ref, b'{"args": [], "kwargs": {}}')
        assert isinstance(msg_id, str) and msg_id
        # Same TaskRef reuses the same actor (cache hit path).
        await adapter.enqueue(ref, b'{"args": [], "kwargs": {}}')
        assert len(adapter._actors) == 1
    finally:
        await adapter.shutdown()


async def test_enqueue_without_callable_raises(
    stub_broker: dict[str, StubBroker],
) -> None:
    adapter = DramatiqAdapter(broker_url="redis://x")
    await adapter.startup(None)
    try:
        bare = TaskRef(module="m", name="n", fn=None)
        with pytest.raises(RuntimeError, match="no callable bound"):
            await adapter.enqueue(bare, b"{}")
    finally:
        await adapter.shutdown()


async def test_schedule_computes_delay(stub_broker: dict[str, StubBroker]) -> None:
    called: list[tuple[Any, ...]] = []
    ref = _make_ref("later", called)
    when = datetime.now(timezone.utc) + timedelta(seconds=5)

    adapter = DramatiqAdapter(broker_url="redis://x")
    await adapter.startup(None)
    try:
        msg_id = await adapter.schedule(ref, when, b'{"args": [], "kwargs": {}}')
        assert msg_id
    finally:
        await adapter.shutdown()


async def test_schedule_clamps_negative_delay(
    stub_broker: dict[str, StubBroker],
) -> None:
    called: list[tuple[Any, ...]] = []
    ref = _make_ref("past", called)
    when = datetime.now(timezone.utc) - timedelta(minutes=1)

    adapter = DramatiqAdapter(broker_url="redis://x")
    await adapter.startup(None)
    try:
        msg_id = await adapter.schedule(ref, when, b'{"args": [], "kwargs": {}}')
        assert msg_id
    finally:
        await adapter.shutdown()


async def test_cron_registers_actor_only(stub_broker: dict[str, StubBroker]) -> None:
    called: list[tuple[Any, ...]] = []
    ref = _make_ref("every", called)

    adapter = DramatiqAdapter(broker_url="redis://x")
    await adapter.startup(None)
    try:
        await adapter.cron(ref, "*/5 * * * *")
        assert "tests.every" in adapter._actors
    finally:
        await adapter.shutdown()


async def test_eager_context_swaps_broker(stub_broker: dict[str, StubBroker]) -> None:
    adapter = DramatiqAdapter(broker_url="redis://x")
    await adapter.startup(None)
    try:
        outer = adapter._broker
        async with adapter.eager():
            inner = adapter._broker
            assert inner is not outer
            assert isinstance(inner, StubBroker)
        assert adapter._broker is outer
    finally:
        await adapter.shutdown()


async def test_status_returns_pending(stub_broker: dict[str, StubBroker]) -> None:
    adapter = DramatiqAdapter(broker_url="redis://x")
    state = await adapter.status("any-id")
    assert state.state == "pending"


async def test_result_raises_not_implemented(
    stub_broker: dict[str, StubBroker],
) -> None:
    adapter = DramatiqAdapter(broker_url="redis://x")
    with pytest.raises(NotImplementedError, match="Results middleware"):
        await adapter.result("any-id")


def test_plugin_defaults_to_localhost(stub_broker: dict[str, StubBroker]) -> None:
    plugin(types.SimpleNamespace())
    [adapter] = plugin_registry.registered()
    assert isinstance(adapter, DramatiqAdapter)
    assert adapter.broker_url == "redis://localhost"


def test_plugin_reads_redis_url(stub_broker: dict[str, StubBroker]) -> None:
    plugin(types.SimpleNamespace(redis_url="redis://h:1234/0"))
    [adapter] = plugin_registry.registered()
    assert isinstance(adapter, DramatiqAdapter)
    assert adapter.broker_url == "redis://h:1234/0"


def test_plugin_unwraps_secret_url(stub_broker: dict[str, StubBroker]) -> None:
    plugin(types.SimpleNamespace(redis_url=SecretStr("redis://h")))
    [adapter] = plugin_registry.registered()
    assert isinstance(adapter, DramatiqAdapter)
    assert adapter.broker_url == "redis://h"
