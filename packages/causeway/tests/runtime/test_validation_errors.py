"""Field-level 422 validation errors for msgspec + Pydantic bodies."""

# pyright: basic

from __future__ import annotations

import msgspec
import pytest
from starlette.testclient import TestClient

from causeway._runtime import App
from causeway._runtime.runtime import ParamSpec, ValidationError, _convert_primitive


class Inner(msgspec.Struct):
    name: str
    weight: float


class Outer(msgspec.Struct):
    label: str
    items: list[Inner]


def test_missing_top_level_field() -> None:
    app = App()

    @app.post("/posts")
    async def create(data: Outer) -> dict[str, str]:
        return {"label": data.label}

    r = TestClient(app).post("/posts", json={"items": []})
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "body"
    assert body["field"] is not None
    assert "label" in body["field"]


def test_nested_field_type_error() -> None:
    app = App()

    @app.post("/posts")
    async def create(data: Outer) -> dict[str, str]:
        return {"label": data.label}

    payload = {
        "label": "x",
        "items": [
            {"name": "a", "weight": 1.0},
            {"name": "b", "weight": "not-a-number"},
        ],
    }
    r = TestClient(app).post("/posts", json=payload)
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "body"
    # path scoped under the body alias + index + field name
    assert "items" in body["field"]


def test_missing_query_param() -> None:
    from typing import Annotated

    from causeway._runtime.params import Query

    app = App()

    @app.get("/search")
    async def search(q: Annotated[str, Query()]) -> dict[str, str]:
        return {"q": q}

    r = TestClient(app).get("/search")
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "query"
    assert body["field"] == "q"
    assert body["value"] is None


def test_pydantic_field_path() -> None:
    import pydantic

    class CreatePost(pydantic.BaseModel):
        title: str
        author: pydantic.BaseModel  # placeholder, overridden below

    class Author(pydantic.BaseModel):
        name: str
        email: str

    class Post(pydantic.BaseModel):
        title: str
        author: Author

    app = App()

    @app.post("/posts")
    async def create(data: Post) -> dict[str, str]:
        return {"title": data.title}

    r = TestClient(app).post(
        "/posts",
        json={"title": "x", "author": {"name": "ada"}},  # email missing
    )
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "body"
    assert "author.email" in body["field"] or "email" in body["field"]


def test_bad_uuid_path_param_returns_422_not_500() -> None:
    """Path-param convert failure must raise typed ValidationError → 422.

    Regression: the fallback ``msgspec.json.decode`` inside
    ``_convert_query_value`` used to re-raise ``msgspec.ValidationError``
    uncaught, which escaped to the ASGI layer as a 500.
    """
    from uuid import UUID

    app = App()

    @app.get("/items/{id}")
    async def show(id: UUID) -> dict[str, str]:
        return {"id": str(id)}

    r = TestClient(app, raise_server_exceptions=False).get("/items/not-a-uuid")
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "path"
    assert body["field"] == "id"
    assert body["value"] == "not-a-uuid"


def test_bad_list_query_item_returns_422_not_500() -> None:
    """List-valued query item convert failure also surfaces as 422."""
    from typing import Annotated

    from causeway._runtime.params import Query

    app = App()

    @app.get("/search")
    async def search(ids: Annotated[list[int], Query()]) -> dict[str, list[int]]:
        return {"ids": ids}

    r = TestClient(app, raise_server_exceptions=False).get("/search?ids=1&ids=oops")
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "query"
    assert body["field"] == "ids"


def test_bad_bool_query_param_returns_422() -> None:
    app = App()

    @app.get("/search")
    async def search(active: bool) -> dict[str, bool]:
        return {"active": active}

    r = TestClient(app, raise_server_exceptions=False).get("/search?active=maybe")
    assert r.status_code == 422
    body = r.json()
    assert body["location"] == "query"
    assert body["field"] == "active"
    assert body["value"] == "maybe"


def test_validation_error_suppresses_parser_context() -> None:
    spec = ParamSpec(
        name="active",
        alias="active",
        location="query",
        py_type=bool,
        required=True,
        default=None,
    )

    with pytest.raises(ValidationError) as exc_info:
        _convert_primitive("maybe", spec)

    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
