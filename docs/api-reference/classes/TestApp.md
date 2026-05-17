# `TestApp`

In-process ASGI test client. Wraps a `dyadpy.App` and proxies HTTP methods to an `httpx.AsyncClient` over an `ASGITransport`.

```python
from causeway.testing import TestApp

app = TestApp.from_routes("src/app/routes")

r = await app.get("/users")
r = await app.post("/users", json={"name": "ada"})
```

## Constructors

```python
TestApp.from_routes(routes_root: str | Path) -> TestApp
```
Walks `routes_root`, builds a fresh `dyadpy.App`, attaches health endpoints, returns a `TestApp`.

```python
TestApp.wrap(app: dyadpy.App) -> TestApp
```
Wraps an existing `dyadpy.App` — useful for app-factory patterns.

## HTTP methods

All async, all return `httpx.Response`:

```python
await app.get(path, **kwargs)
await app.post(path, **kwargs)
await app.put(path, **kwargs)
await app.patch(path, **kwargs)
await app.delete(path, **kwargs)
await app.request(method, path, **kwargs)
```

`**kwargs` are forwarded to `httpx.AsyncClient.request` — pass `json=`, `headers=`, `params=`, etc.

## Overriding DI providers

```python
async with app.override(get_session, fake_session):
    r = await app.post("/users", json={"name": "ada"})
```

Swaps the provider for the duration of the block. Restoration is exception-safe. Same scope machinery as production — no separate test injection path.

For the "I want this provider to be a literal value" case:

```python
from causeway.testing import stub

async with stub(get_user, fake_admin_user):
    r = await app.get("/admin/stats")
```

## Direct client access

For request shapes the helpers don't cover:

```python
async with app.client() as c:    # httpx.AsyncClient
    r = await c.send(custom_request)
```

## Notes

- The class sets `__test__ = False` so pytest's auto-collector doesn't treat it as a test class.
- A `TestApp` is independent per instance — build one per test (or per fixture).

## See also

- [Testing](../../building/testing/index.md)
- [Inline scenarios](../../building/testing/inline-scenarios.md) — for co-located tests with a richer DSL.
- [`tasks_eager`](../functions/tasks-eager.md)
