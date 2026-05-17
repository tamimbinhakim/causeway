"""Tests for the ``IdempotencyMiddleware`` request-replay middleware."""

from __future__ import annotations

from typing import Any

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from causeway.middleware import IdempotencyMiddleware


class _MemoryKV:
    """Bytes-keyed in-memory KV that matches the ``KV`` Protocol surface."""

    contract_version = "v1.0"

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return True

    async def get(self, key: str) -> bytes | None:
        return self.store.get(key)

    async def set(self, key: str, value: bytes, *, ttl: int | None = None) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def incr(self, key: str, by: int = 1) -> int:
        cur = int(self.store.get(key, b"0").decode())
        cur += by
        self.store[key] = str(cur).encode()
        return cur

    async def expire(self, key: str, ttl: int) -> None: ...


def _request(method: str, path: str, body: bytes, *, idempotency_key: str | None = None) -> Request:
    headers = [(b"content-type", b"application/json")]
    if idempotency_key is not None:
        headers.append((b"idempotency-key", idempotency_key.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
    }
    sent = {"done": False}

    async def receive() -> dict[str, Any]:
        if sent["done"]:
            return {"type": "http.disconnect"}
        sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


@pytest.mark.asyncio
async def test_same_key_same_body_replays() -> None:
    kv = _MemoryKV()
    mw = IdempotencyMiddleware(kv=kv)
    calls = {"n": 0}

    async def handler(_req: Request) -> Response:
        calls["n"] += 1
        return JSONResponse({"id": calls["n"]})

    r1 = await mw(_request("POST", "/x", b'{"a":1}', idempotency_key="k1"), handler)
    r2 = await mw(_request("POST", "/x", b'{"a":1}', idempotency_key="k1"), handler)

    assert calls["n"] == 1
    assert r1.body == r2.body
    assert r1.status_code == r2.status_code == 200


@pytest.mark.asyncio
async def test_same_key_different_body_conflicts() -> None:
    kv = _MemoryKV()
    mw = IdempotencyMiddleware(kv=kv)

    async def handler(_req: Request) -> Response:
        return JSONResponse({"ok": True})

    await mw(_request("POST", "/x", b'{"a":1}', idempotency_key="k1"), handler)
    conflict = await mw(_request("POST", "/x", b'{"a":2}', idempotency_key="k1"), handler)

    assert conflict.status_code == 422
    assert b"idempotency_key_conflict" in conflict.body


@pytest.mark.asyncio
async def test_no_header_passes_through() -> None:
    kv = _MemoryKV()
    mw = IdempotencyMiddleware(kv=kv)
    calls = {"n": 0}

    async def handler(_req: Request) -> Response:
        calls["n"] += 1
        return JSONResponse({"id": calls["n"]})

    await mw(_request("POST", "/x", b'{"a":1}'), handler)
    await mw(_request("POST", "/x", b'{"a":1}'), handler)
    assert calls["n"] == 2
    assert kv.store == {}


@pytest.mark.asyncio
async def test_safe_method_passes_through() -> None:
    kv = _MemoryKV()
    mw = IdempotencyMiddleware(kv=kv)

    async def handler(_req: Request) -> Response:
        return JSONResponse({"ok": True})

    await mw(_request("GET", "/x", b"", idempotency_key="k1"), handler)
    assert kv.store == {}


@pytest.mark.asyncio
async def test_error_responses_are_not_cached() -> None:
    kv = _MemoryKV()
    mw = IdempotencyMiddleware(kv=kv)
    calls = {"n": 0}

    async def handler(_req: Request) -> Response:
        calls["n"] += 1
        return JSONResponse({"oops": True}, status_code=500)

    await mw(_request("POST", "/x", b'{"a":1}', idempotency_key="k1"), handler)
    await mw(_request("POST", "/x", b'{"a":1}', idempotency_key="k1"), handler)
    assert calls["n"] == 2
    assert kv.store == {}


@pytest.mark.asyncio
async def test_scopes_by_method_and_path() -> None:
    kv = _MemoryKV()
    mw = IdempotencyMiddleware(kv=kv)
    seen: list[str] = []

    async def handler(req: Request) -> Response:
        seen.append(req.url.path)
        return JSONResponse({"path": req.url.path})

    await mw(_request("POST", "/a", b"{}", idempotency_key="k"), handler)
    await mw(_request("POST", "/b", b"{}", idempotency_key="k"), handler)
    # Same key, different paths → two distinct cache entries, handler ran twice.
    assert seen == ["/a", "/b"]
    assert len(kv.store) == 2
