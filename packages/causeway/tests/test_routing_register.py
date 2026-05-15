"""End-to-end: discovered routes register onto a dyadpy.App and respond."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from dyadpy import App

from causeway.routing import discover, register


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


@pytest.mark.asyncio
async def test_full_path_get_request_lands(tmp_path: Path) -> None:
    routes = tmp_path / "routes"
    _write(
        routes,
        "users/[id].py",
        """from causeway import get
from msgspec import Struct

class User(Struct):
    id: str
    name: str

@get
async def show(id: str) -> User:
    return User(id=id, name="ada")
""",
    )

    app = App()
    register(app, discover(routes))

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/users/u123")
    assert resp.status_code == 200
    assert resp.json() == {"id": "u123", "name": "ada"}


@pytest.mark.asyncio
async def test_guard_short_circuits(tmp_path: Path) -> None:
    """The guard raises; the handler body must not run.

    The HTTP-status mapping for guard-raised exceptions belongs to the error
    renderer slice — here we verify the short-circuit semantics directly by
    invoking the discovered route's wrapped handler. A passing test proves:
    (a) guards are composed onto the handler, (b) a guard raise propagates
    out, (c) the body is never reached.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "_middleware.py",
        """from causeway import guard

@guard
async def deny(req):
    raise PermissionError("nope")

middleware = [deny]
""",
    )
    _write(
        routes,
        "index.py",
        """from causeway import get

@get
async def r() -> dict:
    raise AssertionError("handler body must not run when a guard denies")
""",
    )

    found = discover(routes)
    assert len(found.routes) == 1
    route = found.routes[0]

    # The wrapped handler reads the active Request from dyadpy's contextvar
    # when one isn't present in the handler signature. Simulate that here.
    from dataclasses import dataclass

    from dyadpy.context import Context, current_context_var

    @dataclass
    class _FakeReq:
        headers: dict[str, str]
        url: str

    token = current_context_var.set(Context(request=_FakeReq(headers={}, url="http://t/")))  # type: ignore[arg-type]
    try:
        with pytest.raises(PermissionError, match="nope"):
            await route.handler()
    finally:
        current_context_var.reset(token)
