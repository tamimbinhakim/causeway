"""Reference :class:`~causeway.contracts.Webhooks` adapter + signing helpers.

The signing format is Stripe-style: ``v1,<hex(hmac_sha256(secret, f"{ts}.{body}"))>``
in ``X-Causeway-Signature``, paired with ``X-Causeway-Timestamp``. The verifier
rejects timestamps older than ``max_skew_seconds`` to make replay attacks
impractical.

:class:`InMemoryWebhooks` is the reference adapter: in-process queue, immediate
delivery via ``httpx``, exponential backoff retries, state in a dict. Use it
for tests, demos, and single-process apps. Durable delivery (Postgres, SQS,
Redis Streams) belongs in a sibling plugin.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, ClassVar

import msgspec

from causeway.contracts import DeliveryState, WebhookDelivery
from causeway.errors import Unauthorized

_log = logging.getLogger("causeway.webhooks")

# Stripe's schedule, compressed: five attempts over ~5 hours.
_RETRY_DELAYS_SECONDS = (10, 60, 300, 1800, 14400)

SIGNATURE_HEADER = "x-causeway-signature"
TIMESTAMP_HEADER = "x-causeway-timestamp"


def sign_payload(
    secret: str,
    body: bytes,
    *,
    timestamp: int | None = None,
) -> tuple[str, str]:
    """Produce the ``(signature, timestamp)`` headers for an outgoing webhook.

    The timestamp defaults to ``time.time()``; callers pass an explicit value
    only in tests, where deterministic output matters.
    """
    ts = str(int(timestamp if timestamp is not None else time.time()))
    mac = hmac.new(secret.encode("utf-8"), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"v1,{mac}", ts


def verify_signature(
    secret: str,
    body: bytes,
    signature: str | None,
    timestamp: str | None,
    *,
    max_skew_seconds: int = 300,
    now: int | None = None,
) -> None:
    """Raise :class:`Unauthorized` unless the signature checks out.

    Two failure modes: a missing/malformed signature, and a stale or
    tampered one. Both surface as 401 — clients shouldn't be able to tell
    them apart.
    """
    if not signature or not timestamp:
        raise Unauthorized("missing webhook signature")
    try:
        ts_int = int(timestamp)
    except ValueError as exc:
        raise Unauthorized("malformed webhook timestamp") from exc

    current = int(now if now is not None else time.time())
    if abs(current - ts_int) > max_skew_seconds:
        raise Unauthorized("webhook timestamp outside allowed skew")

    if not signature.startswith("v1,"):
        raise Unauthorized("unsupported webhook signature version")

    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature[3:]):
        raise Unauthorized("webhook signature mismatch")


@dataclass(slots=True)
class _Endpoint:
    url: str
    secret: str
    events: list[str]
    enabled: bool = True


@dataclass(slots=True)
class _Delivery:
    delivery_id: str
    endpoint_id: str
    event: str
    payload: dict[str, Any]
    attempts: int = 0
    state: DeliveryState = "pending"
    last_error: str | None = None
    next_retry_at: datetime | None = None
    idempotency_key: str | None = None
    task: asyncio.Task[None] | None = field(default=None, repr=False)


class InMemoryWebhooks:
    """In-process webhook delivery + signature verification.

    Schedules each delivery as an ``asyncio.Task`` that walks the retry
    schedule until the endpoint accepts the call or the retries run out.
    Suitable for tests, demos, and single-process apps; multi-process or
    durable delivery needs a sibling plugin (e.g. ``causeway-webhooks-pg``).
    """

    contract_version: ClassVar[str] = "v1.0"

    def __init__(self, *, http_client: Any = None) -> None:
        # httpx is a soft dependency; accept any duck with
        # ``post(url, content=..., headers=...) -> Response``. Tests inject a fake.
        self._http = http_client
        self._endpoints: dict[str, _Endpoint] = {}
        self._deliveries: dict[str, _Delivery] = {}
        self._seen_idempotency: dict[tuple[str, str], str] = {}

    async def startup(self, settings: Any) -> None: ...

    async def shutdown(self) -> None:
        for delivery in list(self._deliveries.values()):
            task = delivery.task
            if task is not None and not task.done():
                task.cancel()
        client = self._http
        if client is not None and hasattr(client, "aclose"):
            try:
                await client.aclose()
            except Exception:
                _log.warning("InMemoryWebhooks: error closing http client", exc_info=True)

    async def ready(self) -> bool:
        return True

    async def register_endpoint(
        self,
        endpoint_id: str,
        *,
        url: str,
        secret: str,
        events: list[str],
    ) -> None:
        self._endpoints[endpoint_id] = _Endpoint(url=url, secret=secret, events=list(events))

    async def disable_endpoint(self, endpoint_id: str) -> None:
        ep = self._endpoints.get(endpoint_id)
        if ep is not None:
            ep.enabled = False

    async def send(
        self,
        endpoint_id: str,
        event: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> str:
        if idempotency_key is not None:
            existing = self._seen_idempotency.get((endpoint_id, idempotency_key))
            if existing is not None:
                return existing

        delivery_id = uuid.uuid4().hex
        delivery = _Delivery(
            delivery_id=delivery_id,
            endpoint_id=endpoint_id,
            event=event,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        self._deliveries[delivery_id] = delivery
        if idempotency_key is not None:
            self._seen_idempotency[(endpoint_id, idempotency_key)] = delivery_id

        # Fire-and-forget; the worker logs its own errors so callers don't await.
        delivery.task = asyncio.create_task(self._deliver(delivery))
        return delivery_id

    async def delivery_status(self, delivery_id: str) -> WebhookDelivery:
        d = self._deliveries.get(delivery_id)
        if d is None:
            return WebhookDelivery(
                delivery_id=delivery_id,
                state="failed",
                attempts=0,
                last_error="unknown delivery id",
            )
        return WebhookDelivery(
            delivery_id=d.delivery_id,
            state=d.state,
            attempts=d.attempts,
            last_error=d.last_error,
            next_retry_at=d.next_retry_at,
        )

    def verify_incoming(
        self,
        req: Any,
        *,
        secret: str,
        max_skew_seconds: int = 300,
    ) -> bytes:
        """Verify the request's HMAC + timestamp and return the raw body.

        Accepts either a Starlette ``Request`` (synchronously available bytes
        on ``req._body``) or any object with ``.headers`` and ``.body`` —
        the contract documents the surface, not the type.
        """
        body = _extract_body(req)
        headers = _headers(req)
        verify_signature(
            secret,
            body,
            headers.get(SIGNATURE_HEADER),
            headers.get(TIMESTAMP_HEADER),
            max_skew_seconds=max_skew_seconds,
        )
        return body

    async def _deliver(self, delivery: _Delivery) -> None:
        endpoint = self._endpoints.get(delivery.endpoint_id)
        if endpoint is None or not endpoint.enabled:
            delivery.state = "failed"
            delivery.last_error = "endpoint disabled or unknown"
            return

        body = msgspec.json.encode({"event": delivery.event, "data": delivery.payload})
        for attempt, delay in enumerate((0, *_RETRY_DELAYS_SECONDS), start=1):
            if delay:
                delivery.next_retry_at = datetime.fromtimestamp(
                    time.time() + delay,
                    tz=UTC,
                )
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    delivery.state = "failed"
                    delivery.last_error = "cancelled"
                    raise

            delivery.state = "in_flight"
            delivery.attempts = attempt
            sig, ts = sign_payload(endpoint.secret, body)
            try:
                ok = await self._post(endpoint.url, body, sig, ts)
            except Exception as exc:
                delivery.last_error = repr(exc)
                continue
            if ok:
                delivery.state = "delivered"
                delivery.last_error = None
                delivery.next_retry_at = None
                return
            delivery.last_error = "non-2xx response"

        delivery.state = "failed"
        delivery.next_retry_at = None

    async def _post(self, url: str, body: bytes, signature: str, timestamp: str) -> bool:
        client = self._http
        if client is None:
            # Lazy so httpx is only required when the adapter is actually used.
            import httpx

            client = httpx.AsyncClient(timeout=10.0)
            self._http = client
        resp = await client.post(
            url,
            content=body,
            headers={
                SIGNATURE_HEADER: signature,
                TIMESTAMP_HEADER: timestamp,
                "content-type": "application/json",
            },
        )
        status = getattr(resp, "status_code", 0)
        return 200 <= status < 300


def _extract_body(req: Any) -> bytes:
    body = getattr(req, "_body", None)
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    body = getattr(req, "body", None)
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    if callable(body):
        # Verification is sync — Starlette's async ``request.body()`` must be awaited
        # by the caller first so the bytes land on ``req._body``.
        msg = "verify_incoming needs the body already buffered; await request.body() first"
        raise RuntimeError(msg)
    return b""


def _headers(req: Any) -> dict[str, str]:
    raw = getattr(req, "headers", {})
    with contextlib.suppress(Exception):
        return {k.lower(): v for k, v in dict(raw).items()}
    return {}


def new_secret() -> str:
    """Generate a fresh URL-safe secret for a new webhook endpoint."""
    return secrets.token_urlsafe(32)


__all__ = [
    "SIGNATURE_HEADER",
    "TIMESTAMP_HEADER",
    "InMemoryWebhooks",
    "new_secret",
    "sign_payload",
    "verify_signature",
]
