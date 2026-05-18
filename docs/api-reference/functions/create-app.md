# `create_app`

Build a runnable ASGI app from a routes directory.

```python
# src/app/__init__.py
from causeway import create_app
from app.config import settings

app = create_app("src/app/routes", settings=settings)
```

## Signature

```python
create_app(
    routes_root: str | Path = "app/routes",
    *,
    events_root: str | Path = "app/events",
    settings: Any = None,
    diagnostics: bool = True,
    request_id: bool = True,
    error_renderer_: bool = True,
) -> Starlette
```

## Parameters

| Parameter         | Default        | Notes                                                                           |
| ----------------- | -------------- | ------------------------------------------------------------------------------- |
| `routes_root`     | `"app/routes"` | Directory to walk for route files.                                              |
| `events_root`     | `"app/events"` | Directory to walk for event listeners. Missing folder = no event bus installed. |
| `settings`        | `None`         | Your `Settings` instance. Surfaced on the diagnostics page (secrets redacted).  |
| `diagnostics`     | `True`         | Mount `/__causeway`. Disable in production.                                     |
| `request_id`      | `True`         | Install `RequestIdMiddleware` at the app boundary.                              |
| `error_renderer_` | `True`         | Install the problem+json renderer for all exceptions.                           |

## What it does

1. Calls `discover(routes_root)` to walk the tree.
2. Builds a `dyadpy.App` and registers every discovered handler.
3. Attaches `/healthz` and `/readyz` unconditionally; `/__causeway` when `diagnostics=True`.
4. Wraps the dyadpy app in a Starlette `Starlette` with:
   - `RequestIdMiddleware` (when `request_id=True`),
   - every collected class `Middleware` instance from `_middleware.py` files,
   - the problem+json error renderer (when `error_renderer_=True`).
5. If `events_root` exists, walks it with `events.discover(...)` and installs an `InMemoryEventBus` populated with the discovered listeners. Missing folder = no bus installed = `await emit(...)` raises.
6. Wires lifespan: every `_scope.py`'s `startup()` fires on app start (and the event bus starts up here too), `shutdown()` in reverse.

## Return value

A `starlette.applications.Starlette` instance. Run with `uvicorn`:

```bash
uvicorn app:app --reload
```

Or via the CLI (which adds the file watcher and TS codegen):

```bash
causeway dev
```

## See also

- [Architecture — boot pipeline](../../architecture/boot-pipeline.md)
- [`discover`](./discover.md)
- [`emit`](./emit.md) — dispatch an event through the installed bus
- [Events overview](../../building/events/index.md)
- [`RequestIdMiddleware`](../classes/RequestIdMiddleware.md)
