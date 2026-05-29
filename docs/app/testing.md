# Testing

Causeway ships two first-class testing patterns:

1. **Inline scenarios** — write the test next to the route file. Best for single-route tests.
2. **External tests** — a `tests/` directory with pytest fixtures. Best for cross-route flows and heavy setup.

Both compose; most projects use both.

## External tests

```python
# tests/test_users.py
import pytest
from causeway.testing import TestApp, tasks_eager


@pytest.fixture
async def app():
    return TestApp.from_routes("src/app/routes")


async def test_create_user(app):
    async with app.override(get_session, fake_session):
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201


async def test_task_runs_inline(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
```

`TestApp` proxies to an `httpx.AsyncClient` over an `ASGITransport` — no network, no `uvicorn`, just direct ASGI dispatch.

```python
app = TestApp.from_routes("src/app/routes")

await app.get("/users")
await app.post("/users", json={"name": "ada"})
await app.put("/users/1", json={"name": "ada"})
await app.patch("/users/1", json={"name": "ada"})
await app.delete("/users/1")
await app.request("OPTIONS", "/users")
```

## Overriding providers

```python
async with app.override(get_session, lambda: fake_session):
    r = await app.post("/users", json={"name": "ada"})
```

The override swaps the provider for the duration of the block. The same scope machinery handles it as in production — there's no separate "test injection" concept to learn. Restoration is exception-safe.

A convenience helper for the "I want this dependency to be a literal value" case:

```python
from causeway.testing import stub

async with stub(get_user, fake_admin_user):
    r = await app.get("/admin/stats")
```

## Inline scenarios

For single-route tests, co-locate them with the route:

```python
# app/routes/users/index.py
from causeway import get, post, raises
from causeway.errors import BadRequest


@post
@raises(BadRequest)
async def create(data: NewUser) -> User:
    if not data.name or not data.email:
        raise BadRequest("name and email are required")
    return create_user(name=data.name, email=data.email)


if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario

    with scenario("rejects blank fields") as it:
        resp = it.post("/users", json={"name": "", "email": ""})
        expect(resp).body.error.kind == "BadRequest"

    with scenario("creates and reads back") as it:
        new = it.post("/users", json={"name": "ada", "email": "a@x"}).data
        expect(it.get(f"/users/{new.id}")).body.data.email == "a@x"
```

Run with `pytest`. The Causeway pytest plugin finds files containing `if __name__ == "__causeway_test__":` and turns each `with scenario(...)` block into a pytest item. Production imports never trip the guard.

Full guide: [Inline scenarios](./inline-scenarios.md).

## When to choose which

| Use inline scenarios when…         | Use external tests when…          |
| ---------------------------------- | --------------------------------- |
| Testing one route file             | Testing across routes             |
| The test reads the response body   | Heavy fixtures or shared DB state |
| You want the test next to the code | You want cross-cutting setup      |

You don't have to pick globally — most projects use both.

## The `expect` proxy

A chainable assertion DSL:

```python
expect(it.get("/users")).body == [{"id": 1, "name": "ada"}]
expect(it).body.data.name == "ada"          # implicitly `it.last`
expect(it).body.error.kind == "BadRequest"
expect(it).body.items[0].name == "ada"
expect(it).status == 200
expect(it).body.count >= 1
expect("foo") in expect(it).body.tags

# When operators don't fit:
expect(it).body.id.matches(lambda x: isinstance(x, int))
expect(it).body.email.is_not(None)
```

Failures show a unified diff anchored to the JSON path:

```
values differ
  in /app/routes/users/index.py::rejects blank fields
  at .body.error.kind
--- expected
+++ actual
@@ -1 +1 @@
-'BadRequest'
+'NotFound'
```

## Snapshots

For response shapes too tedious to type by hand:

```python
from causeway.testing import expect, scenario, snapshot

with scenario("returns standard envelope") as it:
    expect(it.get("/users/1")).body == snapshot()
```

First run with `pytest --update-snapshots` rewrites the literal in your source:

```python
expect(it.get("/users/1")).body == snapshot({
    "ok": True,
    "data": {"id": 1, "name": "ada", "email": "a@x"},
})
```

Use `...` as a wildcard for fields that vary between runs:

```python
expect(it.get("/users/1")).body == snapshot({
    "ok": True,
    "data": {"id": ..., "name": "ada", "email": ...},
})
```

A bare `snapshot()` without a recorded value fails until you run with `--update-snapshots` — so a teammate who fetches your branch won't silently record their own values.

## Background tasks in tests

Wrap a block in `tasks_eager()` and `.enqueue(...)` runs the task synchronously:

```python
from causeway.testing import tasks_eager

async def test_signup_sends_welcome(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
    # send_welcome already ran; assert on the email mock
```

## Pytest options

The Causeway plugin adds three flags:

| Flag                     | Effect                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| `--causeway-routes=PATH` | Routes root to scan for inline scenarios. Repeatable. Defaults to `app/routes` if not set. |
| `--update-snapshots`     | Record snapshots that have no value; rewrite mismatched ones.                              |
| `--causeway-no-inline`   | Skip inline scenario collection entirely.                                                  |

Pin the routes root in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = ["--causeway-routes=app/routes"]
```

## Next

- [Inline scenarios](./inline-scenarios.md) — full guide.
- [Reference — `TestApp`](../reference/classes/TestApp.md)
- [Reference — `tasks_eager`](../reference/functions/tasks-eager.md)
