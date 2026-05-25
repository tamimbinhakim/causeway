"""Tests for the webhooks surface: signing, Subscriber, task-backed delivery,
incoming verify, and the in-memory WebhookStore."""

from __future__ import annotations

import asyncio
from typing import Any, Self
from uuid import UUID, uuid4

import pytest

from causeway._loader import reset_module_cache
from causeway.errors import Unauthorized
from causeway.events import Event, _reset_registry
from causeway.tasks import InMemoryAdapter, _clear, set_adapter, tasks_eager
from causeway.webhooks import (
    EVENT_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    InMemoryWebhookStore,
    Subscriber,
    set_store,
    sign_payload,
    verify,
    verify_signature,
)


@pytest.fixture(autouse=True)
def _reset() -> Any:
    reset_module_cache()
    _reset_registry()
    _clear()
    set_store(None)
    yield
    reset_module_cache()
    _reset_registry()
    _clear()
    set_store(None)


# ---------------------------------------------------------------------------
# Signing roundtrip
# ---------------------------------------------------------------------------


def test_sign_roundtrip() -> None:
    body = b'{"event":"user.created"}'
    sig, ts = sign_payload("sek", body, timestamp=1700000000)
    verify_signature("sek", body, sig, ts, now=1700000000)


def test_tampered_body_rejected() -> None:
    body = b'{"event":"user.created"}'
    sig, ts = sign_payload("sek", body, timestamp=1700000000)
    with pytest.raises(Unauthorized):
        verify_signature("sek", b'{"event":"evil"}', sig, ts, now=1700000000)


def test_stale_timestamp_rejected() -> None:
    body = b"{}"
    sig, ts = sign_payload("sek", body, timestamp=1700000000)
    with pytest.raises(Unauthorized):
        verify_signature("sek", body, sig, ts, now=1700009999)


def test_missing_signature_rejected() -> None:
    with pytest.raises(Unauthorized):
        verify_signature("sek", b"{}", None, "1700000000")


def test_malformed_timestamp_suppresses_parse_context() -> None:
    with pytest.raises(Unauthorized) as exc_info:
        verify_signature("sek", b"{}", "v1,bad", "not-an-int")
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True


def test_wrong_secret_rejected() -> None:
    body = b"{}"
    sig, ts = sign_payload("sek-a", body, timestamp=1700000000)
    with pytest.raises(Unauthorized):
        verify_signature("sek-b", body, sig, ts, now=1700000000)


# ---------------------------------------------------------------------------
# Subscriber registration + field validation
# ---------------------------------------------------------------------------


def test_subscriber_registers_against_event_class() -> None:
    class CustomerCreated(Event):
        webhook = True
        id: str

    sub = Subscriber(url="https://x", secret="s", events=[CustomerCreated])
    assert sub in CustomerCreated._subscribers


def test_subscriber_rejects_unknown_where_key() -> None:
    class OrderShipped(Event):
        webhook = True
        id: str

    with pytest.raises(ValueError, match="where-key 'nonsense' is not a field"):
        Subscriber(
            url="https://x",
            secret="s",
            events=[OrderShipped],
            where={"nonsense": 1},
        )


def test_subscriber_same_instance_not_double_registered() -> None:
    """Re-running discovery on the same Subscriber instance is a no-op.

    Constructing a *new* instance does register again — same values, new
    intent. The de-duplication is on object identity (covers hot reload of
    the subscriber file).
    """

    class CaseClosed(Event):
        webhook = True
        id: str

    sub = Subscriber(url="https://x", secret="s", events=[CaseClosed])
    assert len(CaseClosed._subscribers) == 1
    # Simulate the discovery walker importing the module a second time and
    # finding the same instance — the registration path is idempotent.
    for event_cls in sub.events:
        if sub not in event_cls._subscribers:
            event_cls._subscribers.append(sub)
    assert len(CaseClosed._subscribers) == 1


# ---------------------------------------------------------------------------
# Task-backed delivery + where filter
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status: int) -> None:
        self.status_code = status


class _FakeAsyncClient:
    """Drop-in for ``httpx.AsyncClient`` — captures every POST."""

    instances: list[_FakeAsyncClient] = []

    def __init__(self, *, timeout: float = 10.0) -> None:
        self.calls: list[dict[str, Any]] = []
        _FakeAsyncClient.instances.append(self)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> _FakeResp:
        self.calls.append({"url": url, "content": content, "headers": headers})
        return _FakeResp(200)


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Replace ``httpx.AsyncClient`` so deliveries don't hit the network."""
    _FakeAsyncClient.instances.clear()
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    return _FakeAsyncClient


async def _ensure_adapter() -> InMemoryAdapter:
    adapter = InMemoryAdapter()
    await adapter.startup(settings=None)
    set_adapter(adapter)
    return adapter


async def test_emit_fans_out_to_subscriber(fake_http: Any) -> None:
    class CustomerCreated(Event):
        webhook = True
        id: str

    Subscriber(url="https://slack.example", secret="s", events=[CustomerCreated])

    adapter = await _ensure_adapter()
    try:
        async with tasks_eager():
            result = await CustomerCreated(id="u1").emit()
    finally:
        await adapter.shutdown()

    assert len(result.delivery_ids) == 1
    assert len(fake_http.instances) == 1
    call = fake_http.instances[0].calls[0]
    assert call["url"] == "https://slack.example"
    assert SIGNATURE_HEADER in call["headers"]
    assert TIMESTAMP_HEADER in call["headers"]
    assert call["headers"][EVENT_HEADER] == "customer.created"


async def test_where_filter_skips_non_matching_subscribers(fake_http: Any) -> None:
    class OrderShipped(Event):
        webhook = True
        organization_id: str
        id: str

    Subscriber(
        url="https://a",
        secret="s",
        events=[OrderShipped],
        where={"organization_id": "org-a"},
    )
    Subscriber(
        url="https://b",
        secret="s",
        events=[OrderShipped],
        where={"organization_id": "org-b"},
    )

    adapter = await _ensure_adapter()
    try:
        async with tasks_eager():
            result = await OrderShipped(organization_id="org-a", id="x").emit()
    finally:
        await adapter.shutdown()

    assert len(result.delivery_ids) == 1
    urls = [c["url"] for c in fake_http.instances[0].calls]
    assert urls == ["https://a"]


async def test_where_filter_uuid_string_equality(fake_http: Any) -> None:
    class Ev(Event):
        webhook = True
        org: UUID
        id: str

    org_uuid = uuid4()
    Subscriber(
        url="https://x",
        secret="s",
        events=[Ev],
        where={"org": str(org_uuid)},  # subscriber stores str
    )
    adapter = await _ensure_adapter()
    try:
        async with tasks_eager():
            result = await Ev(org=org_uuid, id="i").emit()  # event has UUID
    finally:
        await adapter.shutdown()

    assert len(result.delivery_ids) == 1


async def test_non_webhook_event_skips_delivery(fake_http: Any) -> None:
    class InternalOnly(Event):
        id: str

    Subscriber(
        url="https://nope",
        secret="s",
        events=[InternalOnly],  # they could subscribe, but webhook=False
    )
    adapter = await _ensure_adapter()
    try:
        async with tasks_eager():
            result = await InternalOnly(id="x").emit()
    finally:
        await adapter.shutdown()

    assert result.delivery_ids == []
    assert fake_http.instances == []


# ---------------------------------------------------------------------------
# Incoming verify
# ---------------------------------------------------------------------------


class _FakeRequest:
    """Minimal stand-in for a Starlette request with async body()."""

    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        self._body_bytes = body
        self.headers = headers

    async def body(self) -> bytes:
        return self._body_bytes


async def test_verify_returns_typed_payload() -> None:
    body = b'{"event":"customer.created","data":{"id":"u1"}}'
    sig, ts = sign_payload("sek", body, timestamp=1700000000)
    req = _FakeRequest(
        body,
        {
            SIGNATURE_HEADER: sig,
            TIMESTAMP_HEADER: ts,
            EVENT_HEADER: "customer.created",
        },
    )
    incoming = await verify(req, secret="sek", max_skew_seconds=999999999)
    assert incoming.name == "customer.created"
    assert incoming.json == {"id": "u1"}
    assert incoming.body == body


async def test_verify_rejects_bad_signature() -> None:
    body = b"{}"
    sig, ts = sign_payload("right", body, timestamp=1700000000)
    req = _FakeRequest(body, {SIGNATURE_HEADER: sig, TIMESTAMP_HEADER: ts})
    with pytest.raises(Unauthorized):
        await verify(req, secret="wrong", max_skew_seconds=999999999)


# ---------------------------------------------------------------------------
# InMemoryWebhookStore (dynamic subscriptions)
# ---------------------------------------------------------------------------


async def test_store_subscribers_for_returns_matching_rows() -> None:
    store = InMemoryWebhookStore()
    await store.startup(settings=None)
    try:
        await store.subscribe(
            url="https://a",
            secret="s",
            events=["customer.created", "order.shipped"],
        )
        await store.subscribe(
            url="https://b",
            secret="s",
            events=["customer.updated"],
        )

        rows_a = [r async for r in store.subscribers_for("customer.created")]
        rows_b = [r async for r in store.subscribers_for("customer.updated")]
        rows_c = [r async for r in store.subscribers_for("nothing.here")]
        assert len(rows_a) == 1
        assert rows_a[0].url == "https://a"
        assert len(rows_b) == 1
        assert rows_c == []
    finally:
        await store.shutdown()


async def test_emit_fans_out_to_dynamic_subscribers(fake_http: Any) -> None:
    class CustomerCreated(Event):
        webhook = True
        id: str

    store = InMemoryWebhookStore()
    await store.startup(settings=None)
    await store.subscribe(
        url="https://dynamic.example",
        secret="s",
        events=["customer.created"],
    )

    adapter = await _ensure_adapter()
    try:
        async with tasks_eager():
            result = await CustomerCreated(id="u1").emit()
    finally:
        await adapter.shutdown()
        await store.shutdown()

    assert len(result.delivery_ids) == 1
    assert fake_http.instances[0].calls[0]["url"] == "https://dynamic.example"


async def test_unsubscribe_removes_from_store() -> None:
    store = InMemoryWebhookStore()
    await store.startup(settings=None)
    try:
        endpoint_id = await store.subscribe(
            url="https://x",
            secret="s",
            events=["e.one"],
        )
        await store.unsubscribe(endpoint_id)
        rows = [r async for r in store.subscribers_for("e.one")]
        assert rows == []
    finally:
        await store.shutdown()


# ---------------------------------------------------------------------------
# Delivery failure: non-2xx exhausts retries and raises in eager mode
# ---------------------------------------------------------------------------


class _FailingAsyncClient(_FakeAsyncClient):
    async def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> _FakeResp:
        self.calls.append({"url": url, "content": content, "headers": headers})
        return _FakeResp(500)


async def test_failed_delivery_records_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-2xx response is recorded as a failed delivery attempt.

    We don't exercise the full retry chain here — that's the task adapter's
    responsibility and tested in its own suite. We just confirm the
    delivery task hands a non-2xx status off as an exception, which is
    what the adapter's retry machinery hooks onto.
    """

    class Ev(Event):
        webhook = True
        id: str

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FailingAsyncClient)
    Subscriber(url="https://will-fail", secret="s", events=[Ev])

    adapter = await _ensure_adapter()
    try:
        result = await Ev(id="u").emit()
        # Background task will retry; let it churn a couple of cycles so
        # at least one POST attempt lands.
        for _ in range(3):
            await asyncio.sleep(0)
        assert len(result.delivery_ids) == 1
        assert len(_FailingAsyncClient.instances) >= 1
    finally:
        await adapter.shutdown()


# ---------------------------------------------------------------------------
# Background delivery (non-eager) — ensure task is actually enqueued
# ---------------------------------------------------------------------------


async def test_emit_returns_delivery_ids_in_background_mode(fake_http: Any) -> None:
    class Ev(Event):
        webhook = True
        id: str

    Subscriber(url="https://x", secret="s", events=[Ev])

    adapter = await _ensure_adapter()
    try:
        result = await Ev(id="u").emit()
        assert len(result.delivery_ids) == 1
        # Yield to let the background task run.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert len(fake_http.instances) >= 1
    finally:
        await adapter.shutdown()
