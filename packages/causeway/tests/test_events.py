"""Event-dispatch contract tests using the in-memory bus."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from causeway._loader import reset_module_cache
from causeway.events import (
    InMemoryEventBus,
    discover,
    emit,
    register,
    set_bus,
)


@pytest.fixture(autouse=True)
def _reset_loader() -> Any:
    """Drop the shared module cache so each test's tmp tree is loaded fresh."""
    reset_module_cache()
    yield
    reset_module_cache()


@pytest.fixture
async def bus() -> Any:
    b = InMemoryEventBus()
    await b.startup(settings=None)
    set_bus(b)
    yield b
    await b.shutdown()


def _write(root: Path, rel: str, body: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)


async def test_flat_naming_discovery(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "customer.create.py",
        "async def send_welcome(payload): pass\n",
    )
    found = discover(tmp_path)
    assert "customer:create" in found.events
    assert [f.__name__ for f in found.events["customer:create"].listeners] == ["send_welcome"]


async def test_nested_naming_discovery(tmp_path: Path) -> None:
    _write(tmp_path, "customer/create.py", "async def f(p): pass\n")
    found = discover(tmp_path)
    assert "customer:create" in found.events


async def test_folder_and_dotted_combine(tmp_path: Path) -> None:
    _write(tmp_path, "billing/refund.issued.py", "async def f(p): pass\n")
    found = discover(tmp_path)
    assert "billing:refund:issued" in found.events


async def test_multiple_listeners_in_one_file(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "customer.create.py",
        "async def a(p): pass\nasync def b(p): pass\n",
    )
    found = discover(tmp_path)
    names = sorted(f.__name__ for f in found.events["customer:create"].listeners)
    assert names == ["a", "b"]


async def test_same_event_split_across_files_merges(tmp_path: Path) -> None:
    _write(tmp_path, "customer.create.py", "async def a(p): pass\n")
    _write(tmp_path, "customer/create.py", "async def b(p): pass\n")
    found = discover(tmp_path)
    names = sorted(f.__name__ for f in found.events["customer:create"].listeners)
    assert names == ["a", "b"]
    assert len(found.events["customer:create"].sources) == 2


async def test_underscore_files_and_dirs_skipped(tmp_path: Path) -> None:
    _write(tmp_path, "_helper.py", "async def f(p): pass\n")
    _write(tmp_path, "_private/event.py", "async def f(p): pass\n")
    _write(tmp_path, "real.event.py", "async def f(p): pass\n")
    found = discover(tmp_path)
    assert list(found.events) == ["real:event"]


async def test_underscore_prefixed_funcs_skipped(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "customer.create.py",
        "async def public(p): pass\nasync def _private(p): pass\n",
    )
    found = discover(tmp_path)
    names = [f.__name__ for f in found.events["customer:create"].listeners]
    assert names == ["public"]


async def test_non_async_module_attrs_ignored(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "customer.create.py",
        "FOO = 1\ndef sync_fn(p): pass\nasync def listener(p): pass\n",
    )
    found = discover(tmp_path)
    names = [f.__name__ for f in found.events["customer:create"].listeners]
    assert names == ["listener"]


async def test_emit_fans_out(tmp_path: Path, bus: InMemoryEventBus) -> None:
    _write(
        tmp_path,
        "customer.create.py",
        (
            "calls: list = []\n"
            "async def a(p): calls.append(('a', p))\n"
            "async def b(p): calls.append(('b', p))\n"
        ),
    )
    found = discover(tmp_path)
    register(found)
    await emit("customer:create", {"id": 7})

    # The dynamically loaded module isn't in sys.modules; read its
    # globals via any listener's ``__globals__``.
    listeners = found.events["customer:create"].listeners
    calls = listeners[0].__globals__["calls"]
    assert sorted(calls) == [("a", {"id": 7}), ("b", {"id": 7})]


async def test_emit_unknown_event_is_noop(bus: InMemoryEventBus) -> None:
    await emit("nothing:here", {"x": 1})


async def test_listener_failure_propagates(tmp_path: Path, bus: InMemoryEventBus) -> None:
    _write(
        tmp_path,
        "customer.create.py",
        ("async def ok(p): pass\nasync def boom(p): raise RuntimeError('listener failed')\n"),
    )
    register(discover(tmp_path))
    with pytest.raises(RuntimeError, match="listener failed"):
        await emit("customer:create", None)


async def test_emit_without_bus_raises(tmp_path: Path) -> None:
    # No fixture; explicitly reset the var so test order can't help us.
    from causeway.events import _bus_var

    _bus_var.set(None)  # type: ignore[arg-type]
    with pytest.raises(AttributeError):
        # Bus is None → emit will AttributeError on .emit; acceptable surfacing.
        await emit("anything", None)


async def test_missing_events_root_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        discover(tmp_path / "does-not-exist")


async def test_empty_events_root_is_empty(tmp_path: Path) -> None:
    found = discover(tmp_path)
    assert found.events == {}


async def test_listener_can_enqueue_a_task(tmp_path: Path, bus: InMemoryEventBus) -> None:
    """End-to-end: a listener uses task.enqueue to do durable work."""
    from causeway.tasks import InMemoryAdapter, _clear, set_adapter, tasks_eager

    _clear()
    adapter = InMemoryAdapter()
    await adapter.startup(settings=None)
    set_adapter(adapter)
    try:
        # Write a listener file that imports causeway.tasks and enqueues.
        _write(
            tmp_path,
            "customer.create.py",
            (
                "from causeway.tasks import task\n"
                "side: list = []\n"
                "@task()\n"
                "async def remember(x: str) -> None: side.append(x)\n"
                "async def listener(p):\n"
                "    await remember.enqueue(p)\n"
            ),
        )
        register(discover(tmp_path))

        async with tasks_eager():
            await emit("customer:create", "hello")

        # Only ``listener`` is discovered — ``remember`` is a TaskRef, not
        # an async function. Read the sentinel via the listener's globals.
        listeners = next(iter(discover(tmp_path).events.values())).listeners
        assert [f.__name__ for f in listeners] == ["listener"]
        side = listeners[0].__globals__["side"]
        assert side == ["hello"]
    finally:
        await adapter.shutdown()
        _clear()
