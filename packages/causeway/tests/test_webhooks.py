"""Tests for the webhooks adapter + signing helpers."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from causeway.errors import Unauthorized
from causeway.webhooks import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    InMemoryWebhooks,
    sign_payload,
    verify_signature,
)


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


def test_wrong_secret_rejected() -> None:
    body = b"{}"
    sig, ts = sign_payload("sek-a", body, timestamp=1700000000)
    with pytest.raises(Unauthorized):
        verify_signature("sek-b", body, sig, ts, now=1700000000)


class _FakeResp:
    def __init__(self, status: int) -> None:
        self.status_code = status


class _FakeClient:
    def __init__(self, responses: list[int]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, *, content: bytes, headers: dict[str, str]) -> _FakeResp:
        self.calls.append({"url": url, "content": content, "headers": headers})
        return _FakeResp(self.responses.pop(0) if self.responses else 200)

    async def aclose(self) -> None:
        pass


@pytest.mark.asyncio
async def test_send_delivers_on_first_attempt() -> None:
    client = _FakeClient([200])
    wh = InMemoryWebhooks(http_client=client)
    await wh.register_endpoint("ep1", url="https://example.com/hook", secret="sek", events=["*"])
    delivery_id = await wh.send("ep1", "user.created", {"id": "u1"})
    # Let the delivery task run.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    status = await wh.delivery_status(delivery_id)
    assert status.state == "delivered"
    assert status.attempts == 1
    assert len(client.calls) == 1
    headers = client.calls[0]["headers"]
    assert SIGNATURE_HEADER in headers
    assert TIMESTAMP_HEADER in headers


@pytest.mark.asyncio
async def test_send_idempotency_key_dedupes() -> None:
    client = _FakeClient([200, 200])
    wh = InMemoryWebhooks(http_client=client)
    await wh.register_endpoint("ep1", url="https://x", secret="sek", events=["*"])
    d1 = await wh.send("ep1", "user.created", {"id": "u1"}, idempotency_key="k1")
    d2 = await wh.send("ep1", "user.created", {"id": "u1"}, idempotency_key="k1")
    assert d1 == d2


@pytest.mark.asyncio
async def test_disable_endpoint_fails_pending_delivery() -> None:
    client = _FakeClient([200])
    wh = InMemoryWebhooks(http_client=client)
    await wh.register_endpoint("ep1", url="https://x", secret="sek", events=["*"])
    await wh.disable_endpoint("ep1")
    delivery_id = await wh.send("ep1", "user.created", {"id": "u1"})
    await asyncio.sleep(0)
    status = await wh.delivery_status(delivery_id)
    assert status.state == "failed"
    assert client.calls == []
