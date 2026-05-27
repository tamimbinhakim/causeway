"""End-to-end ASGI tests using httpx's in-process transport.

These exercise the actual request path: parameter resolution, msgspec
decoding, response encoding, typed errors, streaming, and DI.
"""

# pyright: basic
# Tests don't need strict typing; handlers are also consumed via decorator side effects.

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

import httpx
import msgspec
import pytest
from starlette.responses import JSONResponse

from causeway._runtime import App, Context, Depends, raises, stream
from causeway._runtime.params import Body, Header


@pytest.fixture
def client_factory():
    def _make(app: App) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    return _make


async def test_unary_get_with_path_param(client_factory):
    app = App()

    @app.get("/users/{user_id}")
    async def get_user(user_id: int) -> dict[str, int]:
        return {"id": user_id}

    async with client_factory(app) as client:
        r = await client.get("/users/42")
    assert r.status_code == 200
    assert r.json() == {"id": 42}


async def test_post_struct_body(client_factory):
    class CreatePost(msgspec.Struct):
        title: str
        body: str
        tags: list[str] = []

    app = App()

    @app.post("/posts")
    async def create(data: CreatePost) -> dict[str, str]:
        return {"title": data.title, "body": data.body}

    async with client_factory(app) as client:
        r = await client.post("/posts", json={"title": "hi", "body": "world"})
    assert r.status_code == 200
    assert r.json() == {"title": "hi", "body": "world"}


async def test_embedded_body_params(client_factory):
    app = App()

    @app.post("/login")
    async def login(
        email: Annotated[str, Body()],
        password: Annotated[str, Body()],
    ) -> dict[str, str]:
        return {"email": email, "pw_len": str(len(password))}

    async with client_factory(app) as client:
        r = await client.post("/login", json={"email": "a@b.com", "password": "secret"})
    assert r.json() == {"email": "a@b.com", "pw_len": "6"}


async def test_query_param_coercion(client_factory):
    app = App()

    @app.get("/search")
    async def search(q: str, limit: int = 10) -> dict[str, int | str]:
        return {"q": q, "limit": limit}

    async with client_factory(app) as client:
        r = await client.get("/search?q=hi&limit=5")
    assert r.json() == {"q": "hi", "limit": 5}


async def test_header_param(client_factory):
    app = App()

    @app.get("/whoami")
    async def whoami(ua: Annotated[str, Header(alias="user-agent")] = "") -> dict[str, str]:
        return {"ua": ua}

    async with client_factory(app) as client:
        r = await client.get("/whoami", headers={"user-agent": "causeway-test"})
    assert r.json() == {"ua": "causeway-test"}


async def test_context_injected(client_factory):
    app = App()

    @app.get("/ctx")
    async def ctx(ctx: Context) -> dict[str, str]:
        return {"path": str(ctx.request.url.path)}

    async with client_factory(app) as client:
        r = await client.get("/ctx")
    assert r.json() == {"path": "/ctx"}


async def test_typed_error_wraps_in_result(client_factory):
    @dataclass
    class PostNotFound(Exception):
        post_id: int

    app = App()

    @app.get("/posts/{post_id}")
    @raises(PostNotFound)
    async def get_post(post_id: int) -> dict[str, int]:
        raise PostNotFound(post_id=post_id)

    async with client_factory(app) as client:
        r = await client.get("/posts/7")
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": False, "error": {"kind": "PostNotFound", "post_id": 7}}


async def test_typed_error_uses_declared_status_and_request_id(client_factory):
    class PostNotFound(Exception):
        status = 404
        code = "post_not_found"

        def __init__(self, post_id: int) -> None:
            super().__init__(f"post {post_id} missing")
            self.post_id = post_id

    app = App()

    @app.get("/posts/{post_id}")
    @raises(PostNotFound)
    async def get_post(post_id: int, ctx: Context) -> dict[str, int]:
        ctx.request.state.request_id = "req-123"
        raise PostNotFound(post_id)

    async with client_factory(app) as client:
        r = await client.get("/posts/7")
    assert r.status_code == 404
    body = r.json()
    assert body == {
        "ok": False,
        "error": {
            "kind": "PostNotFound",
            "post_id": 7,
            "status": 404,
            "code": "post_not_found",
            "request_id": "req-123",
        },
    }


async def test_typed_success_wraps_in_result(client_factory):
    class Err(Exception):
        pass

    app = App()

    @app.get("/ok")
    @raises(Err)
    async def ok_handler() -> int:
        return 99

    async with client_factory(app) as client:
        r = await client.get("/ok")
    assert r.json() == {"ok": True, "data": 99}


async def test_streaming_endpoint_emits_sse(client_factory):
    class Token(msgspec.Struct, tag_field="kind", tag="token"):
        text: str

    class Done(msgspec.Struct, tag_field="kind", tag="done"):
        count: int

    app = App()

    @app.get("/chat")
    async def chat() -> stream[Token | Done]:
        yield Token(text="hello")
        yield Token(text="world")
        yield Done(count=2)

    async with client_factory(app) as client:
        r = await client.get("/chat")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    frames: list[dict] = []
    for chunk in r.text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk or chunk.startswith("event: done"):
            continue
        for line in chunk.splitlines():
            if line.startswith("data: "):
                frames.append(json.loads(line[6:]))
    assert frames == [
        {"kind": "token", "text": "hello"},
        {"kind": "token", "text": "world"},
        {"kind": "done", "count": 2},
    ]


async def test_unhandled_stream_exception_emits_error_frame_and_logs_concisely(
    client_factory,
    caplog,
    capsys,
):
    class Token(msgspec.Struct, tag_field="kind", tag="token"):
        text: str

    app = App()

    @app.get("/chat")
    async def chat(ctx: Context) -> stream[Token]:
        ctx.request.state.request_id = "req-stream"
        yield Token(text="hello")
        raise RuntimeError("stream died")

    caplog.set_level("ERROR", logger="causeway.runtime")
    async with client_factory(app) as client:
        r = await client.get("/chat")

    assert r.status_code == 200
    assert (
        'event: error\ndata: {"kind":"InternalError","message":"internal server error","request_id":"req-stream"}'
        in r.text
    )
    # Logger record: short, structured, easy to grep.
    logged = caplog.text
    assert "RuntimeError: stream died" in logged
    assert "Traceback (most recent call last)" not in logged
    # Rich panel: comprehensive operator-facing detail rendered to stderr.
    panel = capsys.readouterr().err
    assert "RuntimeError" in panel
    assert "stream died" in panel
    assert "GET /chat" in panel
    assert "req-stream" in panel


async def test_depends_resolution(client_factory):
    def db() -> dict[str, str]:
        return {"name": "memdb"}

    app = App()

    @app.get("/db")
    async def get_db(d: dict[str, str] = Depends(db)) -> dict[str, str]:
        return d

    async with client_factory(app) as client:
        r = await client.get("/db")
    assert r.json() == {"name": "memdb"}


async def test_depends_with_generator_teardown(client_factory):
    teardown_log: list[str] = []

    def session() -> Iterator[str]:
        teardown_log.append("open")
        yield "session-1"
        teardown_log.append("close")

    app = App()

    @app.get("/s")
    async def use_session(s: str = Depends(session)) -> dict[str, str]:
        return {"s": s}

    async with client_factory(app) as client:
        r = await client.get("/s")
    assert r.json() == {"s": "session-1"}
    assert teardown_log == ["open", "close"]


async def test_query_param_default_when_missing(client_factory):
    app = App()

    @app.get("/items")
    async def list_items(limit: int = 25) -> dict[str, int]:
        return {"limit": limit}

    async with client_factory(app) as client:
        r = await client.get("/items")
    assert r.json() == {"limit": 25}


async def test_missing_required_query_param_422(client_factory):
    app = App()

    @app.get("/needs")
    async def needs(name: str) -> dict[str, str]:
        return {"name": name}

    async with client_factory(app) as client:
        r = await client.get("/needs")
    assert r.status_code == 422


async def test_unhandled_exception_returns_500_and_logs_concisely(client_factory, caplog, capsys):
    app = App()

    @app.get("/boom")
    async def boom(ctx: Context) -> None:
        ctx.request.state.request_id = "req-500"
        raise RuntimeError("not declared")

    caplog.set_level("ERROR", logger="causeway.runtime")
    async with client_factory(app) as client:
        r = await client.get("/boom")

    assert r.status_code == 500
    assert r.json() == {"detail": "internal server error", "request_id": "req-500"}
    # Logger record: short, structured, easy to grep.
    logged = caplog.text
    assert "RuntimeError: not declared" in logged
    assert "Traceback (most recent call last)" not in logged
    # Rich panel: full operator detail rendered to stderr.
    panel = capsys.readouterr().err
    assert "RuntimeError" in panel
    assert "not declared" in panel
    assert "GET /boom" in panel
    assert "req-500" in panel
    assert "test_runtime.py" in panel


async def test_unhandled_exception_can_use_custom_exception_handler(client_factory, caplog):
    async def render_problem(request, exc):
        request_id = getattr(request.state, "request_id", None)
        body = {
            "title": type(exc).__name__,
            "detail": str(exc),
            "request_id": request_id,
        }
        return JSONResponse(body, status_code=418, media_type="application/problem+json")

    app = App(exception_handler=render_problem)

    @app.get("/boom")
    async def boom(ctx: Context) -> None:
        ctx.request.state.request_id = "req-custom"
        raise RuntimeError("custom render")

    caplog.set_level("ERROR", logger="causeway.runtime")
    async with client_factory(app) as client:
        r = await client.get("/boom")

    assert r.status_code == 418
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json() == {
        "title": "RuntimeError",
        "detail": "custom render",
        "request_id": "req-custom",
    }
    assert "RuntimeError: custom render" not in caplog.text
