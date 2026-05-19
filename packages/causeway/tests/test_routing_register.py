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


@pytest.mark.asyncio
async def test_use_decorator_attaches_guard_per_handler(tmp_path: Path) -> None:
    """``@use(guard_fn)`` attaches a guard to a single handler.

    The guard runs before the body; raising short-circuits, exactly like a
    guard declared in ``_middleware.py`` would, but scoped to this route.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "index.py",
        """from causeway import get, guard, use

@guard
async def deny(req):
    raise PermissionError("scoped nope")

@get
@use(deny)
async def r() -> dict:
    raise AssertionError("body must not run when @use guard denies")
""",
    )

    found = discover(routes)
    assert len(found.routes) == 1
    route = found.routes[0]

    from dataclasses import dataclass

    from dyadpy.context import Context, current_context_var

    @dataclass
    class _FakeReq:
        headers: dict[str, str]
        url: str

    token = current_context_var.set(Context(request=_FakeReq(headers={}, url="http://t/")))  # type: ignore[arg-type]
    try:
        with pytest.raises(PermissionError, match="scoped nope"):
            await route.handler()
    finally:
        current_context_var.reset(token)


def test_use_decorator_validates_entry_types() -> None:
    """``@use(...)`` rejects entries that aren't a Middleware or guard.

    The runtime-checkable ``Middleware`` Protocol only inspects for
    ``__call__``, so bare callables sneak through here — matching the
    behaviour of ``_middleware.py`` validation. Non-callable values are
    the case we can catch.
    """
    from causeway import use

    with pytest.raises(TypeError, match="Middleware instance or a @guard"):
        use("not-a-middleware")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_dependency_binds_resolver_into_handler(tmp_path: Path) -> None:
    """``@dependency`` resolvers are wired into the handler as ``Depends``.

    The handler param ``me: CurrentUser`` resolves to whatever the dependency
    function returns — no ``_scope.py`` needed.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "me.py",
        """from causeway import dependency, get
from starlette.requests import Request

@dependency
async def CurrentUser(req: Request) -> str:
    return "ada"

@get
async def show(me: CurrentUser) -> dict:
    return {"who": me}
""",
    )

    app = App()
    register(app, discover(routes))

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/me")
    assert resp.status_code == 200
    assert resp.json() == {"who": "ada"}


@pytest.mark.asyncio
async def test_dependency_raise_propagates(tmp_path: Path) -> None:
    """A ``@dependency`` resolver that raises short-circuits the handler.

    The body must not run; the exception reaches the error renderer just
    like a guard would.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "me.py",
        """from causeway import dependency, get
from causeway.errors import Unauthorized
from starlette.requests import Request

@dependency
async def CurrentUser(req: Request) -> str:
    raise Unauthorized("sign in")

@get
async def show(me: CurrentUser) -> dict:
    raise AssertionError("body must not run when dependency raises")
""",
    )

    from causeway.errors import Unauthorized

    app = App()
    register(app, discover(routes))

    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        with pytest.raises(Unauthorized, match="sign in"):
            await client.get("/me")


@pytest.mark.asyncio
async def test_guard_does_not_leak_into_class_middleware(tmp_path: Path) -> None:
    """A guard listed alone in ``_middleware.py`` must not crash at request time.

    Regression: ``Middleware`` is a runtime-checkable Protocol matching any
    async callable with ``__call__``, so ``@guard`` functions used to land in
    both the guard partition AND the class-middleware partition — the ASGI
    layer then invoked them with ``(req, call_next)`` and they blew up with
    ``TypeError: takes 1 positional argument but 2 were given``.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "_middleware.py",
        """from causeway import guard

@guard
async def allow(req):
    return None

middleware = [allow]
""",
    )
    _write(
        routes,
        "index.py",
        """from causeway import get

@get
async def r() -> dict:
    return {"ok": True}
""",
    )

    from causeway import create_app

    app = create_app(routes_root=str(routes), diagnostics=False, request_id=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_class_middleware_is_path_gated(tmp_path: Path) -> None:
    """A ``Middleware`` attached via ``@use`` runs only for its handler.

    Regression test for the prior global-ASGI-chain limitation: requests
    to other routes must not see the middleware's side effects (here, a
    response header) even though the middleware is registered on the
    Starlette app.
    """
    routes = tmp_path / "routes"
    _write(
        routes,
        "tagged.py",
        """from causeway import get, use
from starlette.responses import Response

class StampHeader:
    async def __call__(self, req, call_next):
        resp: Response = await call_next(req)
        resp.headers["x-stamp"] = "tagged"
        return resp

@get
@use(StampHeader())
async def r() -> dict:
    return {"ok": True}
""",
    )
    _write(
        routes,
        "plain.py",
        """from causeway import get

@get
async def r() -> dict:
    return {"ok": True}
""",
    )

    from causeway import create_app

    app = create_app(routes_root=str(routes), diagnostics=False, request_id=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        tagged = await client.get("/tagged")
        plain = await client.get("/plain")
    assert tagged.status_code == 200
    assert tagged.headers.get("x-stamp") == "tagged"
    assert plain.status_code == 200
    assert "x-stamp" not in plain.headers, "middleware leaked onto unrelated route"


def test_dependency_requires_return_annotation() -> None:
    """``@dependency`` cannot infer its user-visible type without one."""
    from causeway import dependency

    async def resolver(req):  # type: ignore[no-untyped-def]
        del req
        return "x"

    with pytest.raises(TypeError, match="must declare a return type"):
        dependency(resolver)
