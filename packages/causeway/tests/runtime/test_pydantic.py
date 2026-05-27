"""Pydantic interop tests."""

# pyright: basic

from __future__ import annotations

import json

import pydantic
from starlette.testclient import TestClient

from causeway._runtime import App
from causeway._runtime.codegen import render
from causeway._runtime.ir import build_ir


class CreatePost(pydantic.BaseModel):
    title: str
    body: str
    tags: list[str] = []


class Post(pydantic.BaseModel):
    id: int
    title: str
    body: str
    tags: list[str]


def test_pydantic_body_validates_via_model_validate() -> None:
    app = App()

    @app.post("/posts")
    async def create(data: CreatePost) -> Post:
        return Post(id=1, title=data.title, body=data.body, tags=data.tags)

    client = TestClient(app)
    r = client.post("/posts", json={"title": "hi", "body": "world"})
    assert r.status_code == 200
    assert r.json() == {"id": 1, "title": "hi", "body": "world", "tags": []}


def test_pydantic_response_is_serialized() -> None:
    """A Pydantic instance returned from a handler must round-trip to JSON."""
    app = App()

    @app.get("/post")
    async def one() -> Post:
        return Post(id=42, title="t", body="b", tags=["a"])

    client = TestClient(app)
    r = client.get("/post")
    assert r.status_code == 200
    assert r.json() == {"id": 42, "title": "t", "body": "b", "tags": ["a"]}


def test_pydantic_invalid_body_returns_422_with_field_path() -> None:
    """Pydantic validation errors land as 422 with the offending field path."""
    app = App()

    @app.post("/posts")
    async def create(data: CreatePost) -> Post:
        return Post(id=1, title=data.title, body=data.body, tags=data.tags)

    client = TestClient(app)
    r = client.post("/posts", json={"title": "hi"})  # missing body
    assert r.status_code == 422
    payload = r.json()
    assert payload["location"] == "body"
    assert payload["field"] is not None
    assert "body" in payload["field"]  # the missing field is named in the path


def test_pydantic_schema_in_ir_and_codegen() -> None:
    app = App()

    @app.post("/posts")
    async def create(data: CreatePost) -> Post:
        return Post(id=1, title=data.title, body=data.body, tags=data.tags)

    out = "\n".join(render(build_ir(app)).values())
    assert "export type CreatePost" in out
    assert "export type Post" in out
    assert "title: string" in out
    # IR walked through, no msgspec error
    ir = build_ir(app)
    json.dumps(ir.components)  # serializable
