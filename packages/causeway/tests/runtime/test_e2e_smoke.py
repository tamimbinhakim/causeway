"""End-to-end smoke tests against one realistic causeway app."""

# pyright: basic

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Annotated, Literal

import httpx
import msgspec
import pytest

from causeway._runtime import App, Context, Depends, Form, after, raises, stream
from causeway._runtime.params import Cookie, File, Header, Query, UploadFile


class User(msgspec.Struct):
    id: int
    email: str
    name: str
    role: Literal["admin", "member"]


class CreatePost(msgspec.Struct):
    title: str
    body: str
    tags: list[str] = []


class Post(msgspec.Struct):
    id: int
    author_id: int
    title: str
    body: str
    tags: list[str]
    status: Literal["draft", "published"] = "draft"


class LoginForm(msgspec.Struct):
    email: str
    password: str


class Session(msgspec.Struct):
    token: str
    user_id: int


@dataclass
class Forbidden(Exception):
    reason: str


@dataclass
class PostNotFound(Exception):
    post_id: int


class Tick(msgspec.Struct, tag_field="kind", tag="tick"):
    seq: int


class Done(msgspec.Struct, tag_field="kind", tag="done"):
    total: int


@dataclass
class State:
    users: dict[int, User] = field(default_factory=dict)
    posts: dict[int, Post] = field(default_factory=dict)
    sessions: dict[str, int] = field(default_factory=dict)
    audit: list[str] = field(default_factory=list)


def _seed() -> State:
    state = State()
    state.users[1] = User(id=1, email="alice@x.com", name="Alice", role="admin")
    state.users[2] = User(id=2, email="bob@x.com", name="Bob", role="member")
    return state


def _build_app(state: State) -> App:
    app = App()

    def current_user(authorization: Annotated[str, Header()] = "") -> User:
        """Resolve the caller from `Authorization: Bearer <token>`."""
        if not authorization.startswith("Bearer "):
            raise Forbidden(reason="missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        user_id = state.sessions.get(token)
        if user_id is None:
            raise Forbidden(reason="invalid or expired session")
        return state.users[user_id]

    @app.post("/login")
    @raises(Forbidden)
    async def login(form: Annotated[LoginForm, Form()]) -> Session:
        candidate = next((u for u in state.users.values() if u.email == form.email), None)
        if candidate is None or form.password != "hunter2":
            raise Forbidden(reason="bad credentials")
        token = f"tok-{candidate.id}"
        state.sessions[token] = candidate.id
        return Session(token=token, user_id=candidate.id)

    @app.get("/me")
    @raises(Forbidden)
    async def me(me: User = Depends(current_user)) -> User:
        return me

    @app.post("/posts")
    @raises(Forbidden)
    async def create_post(
        data: CreatePost,
        ctx: Context,
        me: User = Depends(current_user),
    ) -> Post:
        post = Post(
            id=len(state.posts) + 1,
            author_id=me.id,
            title=data.title,
            body=data.body,
            tags=data.tags,
        )
        state.posts[post.id] = post
        ctx.set_status(201)
        ctx.set_header("location", f"/posts/{post.id}")
        after(lambda: state.audit.append(f"post.created:{post.id}"))
        return post

    @app.get("/posts/{post_id}")
    @raises(PostNotFound, Forbidden)
    async def get_post(post_id: int, _me: User = Depends(current_user)) -> Post:
        post = state.posts.get(post_id)
        if post is None:
            raise PostNotFound(post_id=post_id)
        return post

    @app.get("/posts")
    @raises(Forbidden)
    async def list_posts(
        _me: User = Depends(current_user),
        tag: Annotated[list[str], Query()] = None,  # type: ignore[assignment]  # noqa: RUF013
        limit: Annotated[int, Query()] = 50,
    ) -> list[Post]:
        posts = list(state.posts.values())
        if tag:
            posts = [p for p in posts if any(t in p.tags for t in tag)]
        return posts[:limit]

    @app.post("/avatar")
    @raises(Forbidden)
    async def upload_avatar(
        file: Annotated[UploadFile, File()],
        _me: User = Depends(current_user),
    ) -> dict[str, int]:
        try:
            content = await file.read()
            return {"bytes": len(content)}
        finally:
            await file.close()

    @app.get("/feed")
    @raises(Forbidden)
    async def feed(
        count: Annotated[int, Query()] = 3,
        _me: User = Depends(current_user),
    ) -> stream[Tick | Done]:
        async def gen() -> AsyncIterator[Tick | Done]:
            for i in range(count):
                yield Tick(seq=i)
                await asyncio.sleep(0)
            yield Done(total=count)

        async for ev in gen():
            yield ev

    @app.get("/health")
    async def health(trace_id: Annotated[str, Header("x-trace-id")] = "") -> dict[str, str]:
        return {"status": "ok", "trace_id": trace_id}

    @app.get("/preferences")
    async def preferences(theme: Annotated[str, Cookie()] = "light") -> dict[str, str]:
        return {"theme": theme}

    return app


@pytest.fixture
def state() -> State:
    return _seed()


@pytest.fixture
def app(state: State) -> App:
    return _build_app(state)


@pytest.fixture
def client(app: App) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_login_then_me(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/login",
        data={"email": "alice@x.com", "password": "hunter2"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    session = body["data"]
    token = session["token"]

    r = await client.get("/me", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    me = r.json()["data"]
    assert me["email"] == "alice@x.com"
    assert me["role"] == "admin"


async def test_login_with_bad_password_returns_typed_error(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/login",
        data={"email": "alice@x.com", "password": "wrong"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": False, "error": {"kind": "Forbidden", "reason": "bad credentials"}}


async def test_me_without_auth_returns_typed_error(client: httpx.AsyncClient) -> None:
    r = await client.get("/me")
    body = r.json()
    assert body["ok"] is False
    assert body["error"]["kind"] == "Forbidden"
    assert "missing bearer token" in body["error"]["reason"]


async def _login(client: httpx.AsyncClient, email: str = "alice@x.com") -> str:
    r = await client.post("/login", data={"email": email, "password": "hunter2"})
    return r.json()["data"]["token"]


async def test_create_post_sets_status_and_location(
    client: httpx.AsyncClient,
    state: State,
) -> None:
    token = await _login(client)
    r = await client.post(
        "/posts",
        json={"title": "hello", "body": "world", "tags": ["intro", "meta"]},
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.headers["location"] == "/posts/1"
    post = r.json()["data"]
    assert post["author_id"] == 1
    assert post["tags"] == ["intro", "meta"]
    await asyncio.sleep(0.01)
    assert "post.created:1" in state.audit


async def test_get_post_missing_returns_typed_error(client: httpx.AsyncClient) -> None:
    token = await _login(client)
    r = await client.get(
        "/posts/999",
        headers={"authorization": f"Bearer {token}"},
    )
    body = r.json()
    assert body["ok"] is False
    assert body["error"] == {"kind": "PostNotFound", "post_id": 999}


async def test_list_posts_filters_by_repeated_query(client: httpx.AsyncClient) -> None:
    token = await _login(client)
    headers = {"authorization": f"Bearer {token}"}
    await client.post(
        "/posts",
        json={"title": "a", "body": "x", "tags": ["red"]},
        headers=headers,
    )
    await client.post(
        "/posts",
        json={"title": "b", "body": "y", "tags": ["blue"]},
        headers=headers,
    )
    r = await client.get("/posts?tag=red", headers=headers)
    posts = r.json()["data"]
    assert len(posts) == 1
    assert posts[0]["title"] == "a"


async def test_upload_multipart_file(client: httpx.AsyncClient) -> None:
    token = await _login(client)
    r = await client.post(
        "/avatar",
        files={"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"bytes": 8}


async def test_stream_event_sequence(client: httpx.AsyncClient) -> None:
    token = await _login(client)
    async with client.stream(
        "GET",
        "/feed?count=2",
        headers={"authorization": f"Bearer {token}"},
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        raw = b"".join([chunk async for chunk in r.aiter_bytes()])
    text = raw.decode()
    assert '"kind":"tick"' in text
    assert '"seq":0' in text
    assert '"seq":1' in text
    assert '"kind":"done"' in text
    assert '"total":2' in text


async def test_health_reads_header_param(client: httpx.AsyncClient) -> None:
    r = await client.get("/health", headers={"x-trace-id": "abc-123"})
    assert r.json() == {"status": "ok", "trace_id": "abc-123"}


async def test_preferences_reads_cookie(client: httpx.AsyncClient) -> None:
    r = await client.get("/preferences", headers={"cookie": "theme=dark"})
    assert r.json() == {"theme": "dark"}


def test_codegen_for_smoke_app_renders_every_section(app: App) -> None:
    from causeway._runtime.codegen import render
    from causeway._runtime.ir import build_ir

    files = render(build_ir(app))
    out = "\n".join(files.values())

    assert "AUTO-GENERATED" in out
    assert 'from "causeway-ts"' in out
    assert "Result" in files["types.d.ts"]

    assert "export interface ApiRoutes" in out
    assert "export const routeMeta: ReadonlyArray<RouteMeta>" in out
    assert "export async function loadRoute" in out
    assert "export namespace Routes" in out

    for name in ("User", "CreatePost", "Post", "Session", "LoginForm", "Tick", "Done"):
        assert f"export type {name}" in out, f"missing domain type {name}"

    assert "export type Forbidden" in out
    assert "export type PostNotFound" in out

    for route_shape in (
        "login: {",
        "me: {",
        "posts: {",
        "create(",
        "byId(",
        "list(",
        "avatar: {",
        "feed: {",
        "health: {",
        "preferences: {",
    ):
        assert route_shape in out, f"missing route shape {route_shape}"

    for ns in (
        "export namespace login",
        "export namespace getPost",
        "export namespace feed",
    ):
        assert ns in out

    assert "streams: true" in out
    assert "result: true" in out
    assert "formBody: true" in out
