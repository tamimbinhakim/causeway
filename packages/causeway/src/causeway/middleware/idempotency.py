"""``Idempotency-Key`` request replay middleware.

The Stripe-style pattern: clients send ``Idempotency-Key: <opaque>`` on
unsafe methods; the server caches the response under that key and replays
it on retry. Same key + different body is a 422 — the client is reusing a
key for two different operations, almost always a bug.

Cache lookup goes through the registered :class:`~causeway.contracts.KV`
plugin. Errors are *not* cached: a 500 should re-attempt the operation on
retry, not poison the key.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import TYPE_CHECKING, Any

import msgspec
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from starlette.requests import Request

    from causeway.contracts import KV
    from causeway.middleware import CallNext

_log = logging.getLogger("causeway.middleware.idempotency")


class _CachedResponse(msgspec.Struct):
    """JSON-encoded into the KV value. Body is base64 so the record stays text-safe."""

    status: int
    headers: list[list[str]]
    body: str
    body_hash: str


class IdempotencyMiddleware:
    """Replay cached responses for repeated ``Idempotency-Key`` requests.

    Reads the header on the configured methods (POST/PUT/PATCH/DELETE by
    default), hashes the body, and either replays the prior response or runs
    the handler and caches its successful result for ``ttl_seconds``.

    The middleware looks up the :class:`~causeway.contracts.KV` plugin at
    request time so plugin registration order in ``plugins.py`` doesn't
    matter — pass ``kv=`` explicitly for tests that need to inject a fake.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = 86400,
        methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE"),
        header: str = "idempotency-key",
        kv: KV | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.methods = tuple(m.upper() for m in methods)
        self.header = header.lower()
        self._kv = kv
        self.__causeway_idempotency__ = {
            "ttl_seconds": ttl_seconds,
            "methods": self.methods,
            "header": self.header,
        }

    async def __call__(self, req: Request, call_next: CallNext) -> Response:
        if req.method.upper() not in self.methods:
            return await call_next(req)
        key = req.headers.get(self.header)
        if not key:
            return await call_next(req)

        kv = self._kv or self._lookup_kv()
        if kv is None:
            # Better to serve the request unprotected than to 500 a working endpoint.
            _log.warning("IdempotencyMiddleware: no KV plugin registered; passing through")
            return await call_next(req)

        body = await req.body()
        body_hash = hashlib.sha256(body).hexdigest()
        cache_key = self._cache_key(req, key)

        cached = await kv.get(cache_key)
        if cached is not None:
            record = msgspec.json.decode(cached, type=_CachedResponse)
            if record.body_hash != body_hash:
                return _conflict_response(key)
            return _rehydrate(record)

        # We've already consumed the stream; re-seed it so the handler sees the bytes.
        _replay_body(req, body)

        response = await call_next(req)
        if 200 <= response.status_code < 300:
            await kv.set(
                cache_key,
                _serialize(response, body_hash),
                ttl=self.ttl_seconds,
            )
        return response

    def _cache_key(self, req: Request, key: str) -> str:
        # Scope by (method, path) so the same key on different endpoints can't collide.
        return f"idem:{req.method.upper()}:{req.url.path}:{key}"

    def _lookup_kv(self) -> KV | None:
        from causeway.contracts import KV as KVProto
        from causeway.plugins import registered

        for adapter in registered():
            if isinstance(adapter, KVProto):
                return adapter
        return None


def _serialize(response: Response, body_hash: str) -> bytes:
    body = _response_body(response)
    headers = [[k, v] for k, v in response.headers.items()]
    record = _CachedResponse(
        status=response.status_code,
        headers=headers,
        body=base64.b64encode(body).decode("ascii"),
        body_hash=body_hash,
    )
    return msgspec.json.encode(record)


def _rehydrate(record: _CachedResponse) -> Response:
    body = base64.b64decode(record.body.encode("ascii"))
    headers = dict(record.headers)
    # Starlette re-derives content-length from the body.
    headers.pop("content-length", None)
    return Response(content=body, status_code=record.status, headers=headers)


def _response_body(response: Response) -> bytes:
    # Streaming responses don't buffer ``.body``; we don't cache them.
    body: Any = getattr(response, "body", None)
    if isinstance(body, (bytes, bytearray, memoryview)):
        return bytes(body)
    return b""


def _conflict_response(key: str) -> Response:
    body: dict[str, Any] = {
        "type": "about:blank#idempotency_key_conflict",
        "title": "idempotency_key_conflict",
        "status": 422,
        "detail": f"Idempotency-Key {key!r} was reused with a different request body",
    }
    return JSONResponse(body, status_code=422, media_type="application/problem+json")


def _replay_body(req: Request, body: bytes) -> None:
    """Re-seed ``request.body()`` so the downstream handler sees the bytes."""

    async def _receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    # Setting the private cache attr is the simplest way to make a second
    # ``await req.body()`` return the bytes we already consumed.
    req._body = body
    req._receive = _receive


__all__ = ["IdempotencyMiddleware"]
