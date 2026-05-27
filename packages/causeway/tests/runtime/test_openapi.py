"""OpenAPI 3.1 exporter tests."""

# pyright: basic

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import msgspec

from causeway._runtime import App, raises, stream
from causeway._runtime.ir import build_ir
from causeway._runtime.openapi import render
from causeway._runtime.params import Query


def test_basic_paths_emit_operation_ids() -> None:
    app = App()

    @app.get("/ping")
    async def ping() -> str:
        return "pong"

    doc = render(build_ir(app))
    assert doc["openapi"] == "3.1.0"
    assert "/ping" in doc["paths"]
    assert doc["paths"]["/ping"]["get"]["operationId"] == "ping"


def test_body_struct_lands_in_request_body() -> None:
    class Create(msgspec.Struct):
        title: str

    app = App()

    @app.post("/posts")
    async def create(data: Create) -> Create:
        return data

    doc = render(build_ir(app))
    op = doc["paths"]["/posts"]["post"]
    assert "requestBody" in op
    assert "application/json" in op["requestBody"]["content"]


def test_streaming_endpoint_documents_sse() -> None:
    class Tick(msgspec.Struct, tag_field="kind", tag="tick"):
        n: int

    app = App()

    @app.get("/ticks")
    async def ticks() -> stream[Tick]:
        yield Tick(n=1)

    op = render(build_ir(app))["paths"]["/ticks"]["get"]
    assert "text/event-stream" in op["responses"]["200"]["content"]


def test_raises_emits_422_response() -> None:
    @dataclass
    class NotFound(Exception):
        post_id: int

    app = App()

    @app.get("/p/{post_id}")
    @raises(NotFound)
    async def get_post(post_id: int) -> dict[str, int]:
        return {"id": post_id}

    op = render(build_ir(app))["paths"]["/p/{post_id}"]["get"]
    assert "422" in op["responses"]


def test_query_param_documented() -> None:
    app = App()

    @app.get("/search")
    async def search(q: Annotated[str, Query()]) -> list[str]:
        return [q]

    op = render(build_ir(app))["paths"]["/search"]["get"]
    params = op["parameters"]
    assert any(p["in"] == "query" and p["name"] == "q" for p in params)
