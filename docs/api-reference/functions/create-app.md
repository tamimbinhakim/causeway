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
    listeners_root: str | Path = "app/listeners",
    subscribers_root: str | Path = "app/subscribers",
    settings: Any = None,
    diagnostics: bool = True,
    request_id: bool = True,
    error_renderer_: bool = True,
) -> Starlette
```

## Parameters

| Parameter          | Default             | Notes                                                                                                         |
| ------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------- |
| `routes_root`      | `"app/routes"`      | Directory to walk for route files.                                                                            |
| `events_root`      | `"app/events"`      | Directory to walk for `Event` subclass files. Missing folder = nothing discovered.                            |
| `listeners_root`   | `"app/listeners"`   | Directory to walk for listener modules. Imports each `.py` so `@listen` decorators run. Missing folder is OK. |
| `subscribers_root` | `"app/subscribers"` | Directory to walk for outbound `Subscriber` declarations. Missing folder is OK.                               |
| `settings`         | `None`              | Your `Settings` instance. Surfaced on the diagnostics page (secrets redacted).                                |
| `diagnostics`      | `True`              | Mount `/__causeway`. Disable in production.                                                                   |
| `request_id`       | `True`              | Install `RequestIdMiddleware` at the app boundary.                                                            |
| `error_renderer_`  | `True`              | Install the problem+json renderer for all exceptions.                                                         |

## What it does

1. Loads plugin entry points, then imports sibling `plugins.py` if present.
2. Imports sibling `lifespan.py` if present.
3. Calls `discover(routes_root)` to walk the tree.
4. Builds a `dyadpy.App` and registers every discovered handler.
5. Attaches `/healthz` and `/readyz` unconditionally; `/__causeway` when `diagnostics=True`.
6. Wraps the dyadpy app in a Starlette `Starlette` with:
   - `RequestIdMiddleware` (when `request_id=True`),
   - every collected class `Middleware` instance from `_middleware.py` files,
   - the problem+json error renderer (when `error_renderer_=True`).
7. Walks the three event-related trees:
   - `events_root`: imports each `.py`; every `Event` subclass registers itself by `wire_name` via `__init_subclass__`.
   - `listeners_root`: imports each `.py` so `@<Event>.listen` decorators run at module scope.
   - `subscribers_root`: imports each `.py` so module-level `Subscriber(...)` instances register against their event classes' `_subscribers` lists.
     No bus is installed — the `Event` class IS the bus. Missing folders are skipped silently.
8. Wires lifespan: app `lifespan.py` startup, plugin startup, then every `_scope.py` `startup()`; shutdown runs the route hooks in reverse, then plugins, then app `lifespan.py`.

## Return value

A `starlette.applications.Starlette` instance. Run directly with `uvicorn`:

```bash
uvicorn app:app
```

Or via the CLI, which adds the smart route watcher, richer logs, diagnostics,
and failed-reload protection:

```bash
causeway dev
```

## See also

- [Architecture — boot pipeline](../../architecture/boot-pipeline.md)
- [`discover`](./discover.md)
- [`Event.emit()`](./emit.md) — fan an event out to listeners + subscribers
- [Events overview](../../building/events/index.md)
- [Webhooks overview](../../building/webhooks/index.md)
- [Subscribers overview](../../building/subscribers/index.md)
- [`RequestIdMiddleware`](../classes/RequestIdMiddleware.md)
