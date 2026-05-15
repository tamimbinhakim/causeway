# Routing

Next.js-style file-based routing for Python. The directory layout is the route table.

## Why files

Three reasons:

1. **It's the most widely understood convention in 2026.** Anyone who has shipped Next.js / Nuxt / SvelteKit recognizes `[id]/`, `(group)/`, `_layout`, `_middleware` instantly.
2. **Routes colocate with their dependencies.** No giant `urls.py` / `routes.ts` file growing forever.
3. **The router itself becomes inspectable.** A folder tree is easier to reason about than a list of `app.add_route(...)` calls.

## File conventions

| Pattern          | URL effect                                                                              | Example                                                       |
| ---------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `index.py`       | the folder's URL itself                                                                 | `users/index.py` → `/users`                                   |
| `foo.py`         | `/foo` segment                                                                          | `health.py` → `/health`                                       |
| `[id].py`        | dynamic segment, typed via the handler signature (the param name must match)            | `[id].py` with `async def show(id: UUID)` → `/users/{id}`     |
| `[id]/...`       | dynamic folder                                                                          | `users/[id]/posts.py` → `/users/{id}/posts`                   |
| `[...rest].py`   | catch-all (reserved for v0.2+)                                                          | not used in v0.1 by default                                   |
| `(group)/`       | folder ignored in URL — group by team / feature / auth without changing the URL surface | `(admin)/stats.py` → `/stats`                                 |
| `_middleware.py` | wraps every route in the subtree                                                        | runs in order: app → tree → leaf                              |
| `_layout.py`     | provides scoped dependencies + lifespan hooks for the subtree                           | exports `provide()` and optionally `startup()` / `shutdown()` |
| `_*.py`          | private — colocated helpers, not routed                                                 | `_db.py`, `_validators.py`                                    |

## Composition order at request time

1. App-level middleware (registered via `plugins.py`).
2. Each `_middleware.py` from root to leaf.
3. Each `_layout.py`'s `provide()`s become available in handler `Annotated[...]` slots.
4. The handler runs.
5. Response unwinds in reverse.

This matches SvelteKit / Next.js layouts and is intuitive for anyone with that background.

## A realistic tree

```
src/app/routes/
├── _middleware.py            # global request id + auth
├── _layout.py                # provides db session
├── index.py                  # /
├── health.py                 # /health
├── users/
│   ├── _middleware.py        # applies to /users/*
│   ├── index.py              # /users
│   ├── [id].py               # /users/{id}
│   └── [id]/
│       └── posts.py          # /users/{id}/posts
├── (admin)/                  # route group (not in URL)
│   ├── _middleware.py        # require_admin guard
│   ├── stats.py              # /stats
│   └── users.py              # /users  (a separate file from users/index.py)
└── chat/
    ├── index.py              # /chat
    └── [thread_id].py        # /chat/{thread_id}
```

## Why brackets

Python doesn't allow brackets in module names, so Quay loads route files via `importlib.util.spec_from_file_location()` rather than ordinary `import` statements. This is well-trodden ground — pytest, fastapi-file-router, and Django's app auto-discovery all rely on the same mechanism.

The trade-off: you can't write `from app.routes.users.[id] import ...`. In practice, route files almost never need to import each other; when they do, Quay provides an explicit alias mechanism.

## Method handlers inside a route file

```python
# src/app/routes/users/[id].py
from typing import Annotated
from uuid import UUID
from msgspec import Struct
from quay import get, patch, delete, raises
from quay.errors import NotFound

class User(Struct):
    id: UUID
    name: str
    email: str

class UserPatch(Struct):
    name: str | None = None
    email: str | None = None

@get
@raises(NotFound)
async def show(id: UUID) -> User: ...

@patch
async def update(id: UUID, data: UserPatch) -> User: ...

@delete
async def remove(id: UUID) -> None: ...
```

Method conflicts (two `@get` decorators in the same file) are caught at boot, not at request time.

## Middleware

```python
# src/app/routes/_middleware.py
from quay import Middleware, Request, Response

class RequestId(Middleware):
    async def __call__(self, req: Request, call_next):
        rid = req.headers.get("x-request-id") or new_id()
        req.state.request_id = rid
        resp: Response = await call_next(req)
        resp.headers["x-request-id"] = rid
        return resp

middleware = [RequestId()]
```

Scoped middleware applies to its subtree only:

```python
# src/app/routes/(admin)/_middleware.py
from quay import guard

@guard
async def require_admin(req):
    user = await current_user(req)
    if not user or not user.is_admin:
        raise PermissionError("admin only")

middleware = [require_admin]
```

## Layouts

```python
# src/app/routes/users/_layout.py
from quay import provide
from app.lib.db import session_factory

@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

Providers from `_layout.py` are request-scoped. Subtree layouts can override parent providers; the inner-most wins.

`_layout.py` may also export `startup()` and `shutdown()` for subtree-scoped lifespan hooks (useful for things like opening a long-lived client only when a specific subtree is active).

## What the router emits

Every discovered handler becomes a Dyadpy route registration. From the IR you get:

- Generated TypeScript client.
- Route diagnostics page at `/__quay`.
- Snapshot tests for the route table (a single JSON fixture).
- Inputs for `quay diff` to flag breaking changes in CI.

The router is the source of truth. Nothing else writes to the IR.
