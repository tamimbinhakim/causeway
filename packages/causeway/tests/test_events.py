"""Tests for the typed Event base class.

Covers: class-based event declaration, wire-name derivation, file-based
discovery + filename validation, @listen registration + signature checks,
and in-process emit fan-out.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from causeway._loader import reset_module_cache
from causeway.events import (
    Event,
    _pascal_to_dotted,
    _pascal_to_snake,
    _reset_registry,
    all_events,
    discover,
    webhookable_events,
)


@pytest.fixture(autouse=True)
def _reset_state() -> Any:
    reset_module_cache()
    _reset_registry()
    yield
    reset_module_cache()
    _reset_registry()


def _write(root: Path, rel: str, body: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)


# ---------------------------------------------------------------------------
# Wire-name derivation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("class_name", "wire"),
    [
        ("CustomerCreated", "customer.created"),
        ("OrderShipped", "order.shipped"),
        ("BillingInvoiceCreated", "billing.invoice.created"),
        ("HttpRequestFailed", "http.request.failed"),
        # Capital runs collapse to one token, same as the PascalCase form.
        ("HTTPRequestFailed", "http.request.failed"),
        ("Started", "started"),
    ],
)
def test_pascal_to_dotted(class_name: str, wire: str) -> None:
    assert _pascal_to_dotted(class_name) == wire


@pytest.mark.parametrize(
    ("class_name", "snake"),
    [
        ("CustomerCreated", "customer_created"),
        ("BillingInvoiceCreated", "billing_invoice_created"),
        ("HttpRequestFailed", "http_request_failed"),
    ],
)
def test_pascal_to_snake(class_name: str, snake: str) -> None:
    assert _pascal_to_snake(class_name) == snake


# ---------------------------------------------------------------------------
# Class registration
# ---------------------------------------------------------------------------


def test_event_subclass_registers() -> None:
    class CustomerCreated(Event):
        id: str

    assert CustomerCreated.wire_name == "customer.created"
    assert CustomerCreated in all_events().values()
    assert CustomerCreated._listeners == []
    assert CustomerCreated._subscribers == []
    assert CustomerCreated.webhook is False


def test_webhook_flag_passes_through() -> None:
    class OrderShipped(Event):
        webhook = True
        id: str

    assert OrderShipped.webhook is True
    assert OrderShipped in webhookable_events()


def test_duplicate_wire_name_raises() -> None:
    class Dup1(Event):
        id: str

    # Different class object but same name → collision.
    with pytest.raises(RuntimeError, match="wire-name collision"):
        # We can't redeclare `class Dup1` in scope, so simulate via type().
        type("Dup1", (Event,), {"__annotations__": {"id": str}})


# ---------------------------------------------------------------------------
# Emit + listeners
# ---------------------------------------------------------------------------


async def test_emit_calls_listeners() -> None:
    class CustomerCreated(Event):
        id: str

    seen: list[str] = []

    @CustomerCreated.listen
    async def remember(p: CustomerCreated) -> None:
        seen.append(p.id)

    await CustomerCreated(id="u1").emit()
    assert seen == ["u1"]


async def test_emit_with_no_listeners_is_noop() -> None:
    class Quiet(Event):
        id: str

    result = await Quiet(id="x").emit()
    assert result.delivery_ids == []


async def test_listener_failure_propagates() -> None:
    class WillBlow(Event):
        x: int

    @WillBlow.listen
    async def boom(_: WillBlow) -> None:
        raise RuntimeError("listener failed")

    with pytest.raises(RuntimeError, match="listener failed"):
        await WillBlow(x=1).emit()


async def test_multiple_listeners_fan_out_concurrently() -> None:
    class Multi(Event):
        n: int

    seen: list[str] = []

    @Multi.listen
    async def a(p: Multi) -> None:
        seen.append(f"a:{p.n}")

    @Multi.listen
    async def b(p: Multi) -> None:
        seen.append(f"b:{p.n}")

    await Multi(n=5).emit()
    assert sorted(seen) == ["a:5", "b:5"]


def test_listen_rejects_sync_function() -> None:
    class S(Event):
        x: int

    with pytest.raises(TypeError, match="async function"):

        @S.listen  # type: ignore[arg-type]
        def not_async(p: S) -> None:
            del p

    assert S._listeners == []


def test_listen_rejects_wrong_arity() -> None:
    class W(Event):
        x: int

    with pytest.raises(TypeError, match="exactly one parameter"):

        @W.listen
        async def two_args(p: W, extra: int) -> None:
            del p, extra


# ---------------------------------------------------------------------------
# File-based discovery
# ---------------------------------------------------------------------------


async def test_discover_picks_up_events(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    _write(
        events_dir,
        "customer_created.py",
        ("from causeway.events import Event\nclass CustomerCreated(Event):\n    id: str\n"),
    )
    snapshot = discover(events_dir)
    assert "customer.created" in snapshot.events
    assert snapshot.events["customer.created"].__name__ == "CustomerCreated"


async def test_discover_imports_listeners(tmp_path: Path) -> None:
    """Listener modules are imported, running their @listen decorators.

    We assert this indirectly: declare the event and a listener for it in
    the *same* file in listeners/ (registry-aware listener — looks the
    event up from the global registry by wire name), then check that the
    event class shows ``len(_listeners) > 0`` after discovery.
    """
    events_dir = tmp_path / "events"
    listeners_dir = tmp_path / "listeners"
    _write(
        events_dir,
        "order_shipped.py",
        ("from causeway.events import Event\nclass OrderShipped(Event):\n    id: str\n"),
    )
    _write(
        listeners_dir,
        "notify.py",
        (
            "from causeway.events import all_events\n"
            "OrderShipped = all_events()['order.shipped']\n"
            "@OrderShipped.listen\n"
            "async def receive(p):\n"
            "    pass\n"
        ),
    )

    snapshot = discover(events_dir, listeners_dir)
    cls = snapshot.events["order.shipped"]
    assert len(cls._listeners) == 1
    assert len(snapshot.listener_modules) == 1


async def test_discover_rejects_filename_mismatch(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    _write(
        events_dir,
        "wrong_name.py",
        ("from causeway.events import Event\nclass CustomerCreated(Event):\n    id: str\n"),
    )
    with pytest.raises(RuntimeError, match="filename mismatch"):
        discover(events_dir)


async def test_discover_rejects_two_classes_in_one_file(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    _write(
        events_dir,
        "combined.py",
        (
            "from causeway.events import Event\n"
            "class Alpha(Event):\n"
            "    x: int\n"
            "class Beta(Event):\n"
            "    y: int\n"
        ),
    )
    with pytest.raises(RuntimeError, match="multiple Event subclasses"):
        discover(events_dir)


def test_discover_missing_root_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        discover(tmp_path / "does-not-exist")


def test_discover_empty_root_is_empty(tmp_path: Path) -> None:
    snapshot = discover(tmp_path)
    assert snapshot.events == {}


def test_discover_skips_underscore_files(tmp_path: Path) -> None:
    events_dir = tmp_path
    _write(
        events_dir,
        "_helper.py",
        "from causeway.events import Event\nclass H(Event):\n    x: int\n",
    )
    snapshot = discover(events_dir)
    assert snapshot.events == {}


# ---------------------------------------------------------------------------
# Struct semantics inherited from msgspec
# ---------------------------------------------------------------------------


def test_event_instances_compare_by_value() -> None:
    class Order(Event):
        id: UUID
        amount: int

    oid = UUID("00000000-0000-0000-0000-000000000001")
    assert Order(id=oid, amount=10) == Order(id=oid, amount=10)
    assert Order(id=oid, amount=10) != Order(id=oid, amount=11)
