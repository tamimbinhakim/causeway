"""Tests for the bottom-level primitives: Bytes, after(), ctx.set_status/header."""

# pyright: basic

from __future__ import annotations

from typing import Annotated

from starlette.testclient import TestClient

from causeway._runtime import App, Bytes, Context, after
from causeway._runtime.codegen import render
from causeway._runtime.ir import build_ir
from causeway._runtime.params import Header

# ----------------------- Bytes ----------------------- #


def test_bytes_body_received_raw() -> None:
    app = App()
    seen: dict[str, bytes] = {}

    @app.post("/webhook")
    async def webhook(body: Bytes, signature: Annotated[str, Header()] = "") -> dict[str, int]:
        seen["body"] = body
        seen["sig"] = signature.encode()
        return {"size": len(body)}

    client = TestClient(app)
    r = client.post(
        "/webhook",
        content=b"\x00\x01\x02not-json-at-all",
        headers={"signature": "v1=deadbeef"},
    )
    assert r.status_code == 200
    assert r.json() == {"size": len(b"\x00\x01\x02not-json-at-all")}
    assert seen["body"] == b"\x00\x01\x02not-json-at-all"
    assert seen["sig"] == b"v1=deadbeef"


def test_bytes_response_sent_raw() -> None:
    payload = b"\x89PNG\r\n\x1a\nfake-image-bytes"
    app = App()

    @app.get("/avatar")
    async def avatar() -> Bytes:
        return payload

    client = TestClient(app)
    r = client.get("/avatar")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/octet-stream")
    assert r.content == payload


def test_bytes_marked_in_ir_and_codegen() -> None:
    app = App()

    @app.get("/blob")
    async def blob() -> Bytes:
        return b""

    @app.post("/upload")
    async def upload(body: Bytes) -> dict[str, int]:
        return {"n": len(body)}

    ir = build_ir(app)
    by_name = {r.name: r for r in ir.routes}
    assert by_name["blob"].binary_response is True
    assert by_name["upload"].binary_body is True

    out = "\n".join(render(ir).values())
    assert "binaryResponse: true" in out
    assert "binaryBody: true" in out


# ----------------------- after() ----------------------- #


def test_after_runs_post_response() -> None:
    fired: list[str] = []
    app = App()

    @app.post("/ping")
    async def ping() -> dict[str, bool]:
        after(lambda: fired.append("a"))
        after(fired.append, "b")
        return {"ok": True}

    client = TestClient(app)
    r = client.post("/ping")
    assert r.status_code == 200
    # Starlette runs background tasks before TestClient returns from .post()
    # in newer versions; either way `fired` is populated by the time we read it.
    assert "a" in fired
    assert "b" in fired


def test_after_via_context_method() -> None:
    fired: list[int] = []
    app = App()

    @app.post("/ping")
    async def ping(ctx: Context) -> dict[str, bool]:
        ctx.after(fired.append, 42)
        return {"ok": True}

    client = TestClient(app)
    client.post("/ping")
    assert fired == [42]


def test_after_outside_handler_raises() -> None:
    import pytest

    with pytest.raises(RuntimeError, match="outside a request handler"):
        after(lambda: None)


# ----------------------- set_status / set_header ----------------------- #


def test_set_status_overrides_response_code() -> None:
    app = App()

    @app.post("/create")
    async def create(ctx: Context) -> dict[str, int]:
        ctx.set_status(201)
        return {"id": 7}

    client = TestClient(app)
    r = client.post("/create")
    assert r.status_code == 201
    assert r.json() == {"id": 7}


def test_set_header_lands_on_response() -> None:
    app = App()

    @app.post("/create")
    async def create(ctx: Context) -> dict[str, int]:
        ctx.set_header("location", "/items/7")
        ctx.set_header("x-request-id", "abc-123")
        return {"id": 7}

    client = TestClient(app)
    r = client.post("/create")
    assert r.headers["location"] == "/items/7"
    assert r.headers["x-request-id"] == "abc-123"


# ----------------------- list query params ----------------------- #


def test_list_query_param_collects_repeats() -> None:
    from causeway._runtime.params import Query

    app = App()

    @app.get("/search")
    async def search(
        tag: Annotated[list[str], Query()] = None,  # type: ignore[assignment]  # noqa: RUF013
    ) -> dict[str, list[str]]:
        return {"tags": tag}

    client = TestClient(app)
    r = client.get("/search?tag=bug&tag=ui")
    assert r.status_code == 200
    assert r.json() == {"tags": ["bug", "ui"]}


def test_list_query_param_converts_items() -> None:
    from causeway._runtime.params import Query

    app = App()

    @app.get("/ids")
    async def ids(
        id: Annotated[list[int], Query()] = None,  # type: ignore[assignment]  # noqa: RUF013
    ) -> dict[str, list[int]]:
        return {"ids": id}

    client = TestClient(app)
    r = client.get("/ids?id=1&id=2&id=42")
    assert r.json() == {"ids": [1, 2, 42]}


def test_list_query_param_default_when_absent() -> None:
    from causeway._runtime.params import Query

    app = App()

    @app.get("/q")
    async def q(
        tag: Annotated[list[str], Query()] = None,  # type: ignore[assignment]  # noqa: RUF013
    ) -> dict[str, list[str]]:
        return {"tags": tag}

    client = TestClient(app)
    r = client.get("/q")
    assert r.json() == {"tags": []}


# ----------------------- set_cookie ----------------------- #


def test_set_cookie_emits_set_cookie_header() -> None:
    app = App()

    @app.post("/login")
    async def login(ctx: Context) -> dict[str, bool]:
        ctx.set_cookie("session", "abc.def.ghi", max_age=3600, http_only=True, secure=True)
        return {"ok": True}

    client = TestClient(app)
    r = client.post("/login")
    set_cookie = r.headers["set-cookie"]
    assert "session=abc.def.ghi" in set_cookie
    assert "Max-Age=3600" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie


def test_set_cookie_multiple() -> None:
    app = App()

    @app.post("/multi")
    async def multi(ctx: Context) -> dict[str, bool]:
        ctx.set_cookie("a", "1")
        ctx.set_cookie("b", "2")
        return {"ok": True}

    client = TestClient(app)
    r = client.post("/multi")
    # Starlette sends one Set-Cookie header per call; httpx merges them with comma.
    raw = r.headers.get_list("set-cookie")
    joined = "\n".join(raw)
    assert "a=1" in joined
    assert "b=2" in joined


# ----------------------- Form[T] ----------------------- #


def test_form_body_decodes_urlencoded() -> None:
    import msgspec

    from causeway._runtime import Form

    class LoginForm(msgspec.Struct):
        email: str
        password: str
        remember_me: bool = False

    app = App()

    @app.post("/login")
    async def login(form: Annotated[LoginForm, Form()]) -> dict[str, object]:
        return {"email": form.email, "remember": form.remember_me}

    client = TestClient(app)
    r = client.post(
        "/login",
        data={"email": "a@b.co", "password": "hunter2", "remember_me": "true"},
    )
    assert r.status_code == 200
    assert r.json() == {"email": "a@b.co", "remember": True}


def test_form_body_marked_in_ir_and_codegen() -> None:
    import msgspec

    from causeway._runtime import Form

    class LoginForm(msgspec.Struct):
        email: str
        password: str

    app = App()

    @app.post("/login")
    async def login(form: Annotated[LoginForm, Form()]) -> dict[str, str]:
        return {"email": form.email}

    ir = build_ir(app)
    assert ir.routes[0].form_body is True
    out = "\n".join(render(ir).values())
    assert "formBody: true" in out
