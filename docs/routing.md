# Routing

File-based routing for Python. The folder tree _is_ the route table — no `urls.py`, no `routes.ts`, no central registration file.

## Why files

Three reasons:

1. **The folder tree is the route table.** What you see on disk is what you serve.
2. **Routes colocate with their dependencies.** Middleware, scoped DI providers, and helpers live next to the handlers they apply to — no giant `urls.py` growing forever.
3. **The router is inspectable.** A folder tree is easier to reason about, diff, and grep than a list of `app.add_route(...)` calls.

The bracket / paren / underscore syntax will look familiar if you've used Next.js or SvelteKit; the conventions translate cleanly to backend semantics.

## File conventions

Two styles, freely mixable in the same tree: **folder style** (Next.js / SvelteKit-flavored) and **dot-flat style** (TanStack Router-flavored). Pick whichever reads better for the route — most projects use folders for deep, group-heavy trees and dot-flat for shallow, parameter-light endpoints.

### Folder style

| Pattern          | URL effect                                                                              | Example                                                       |
| ---------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `index.py`       | the folder's URL itself                                                                 | `users/index.py` → `/users`                                   |
| `foo.py`         | `/foo` segment                                                                          | `health.py` → `/health`                                       |
| `[id].py`        | dynamic segment, typed via the handler signature (the param name must match)            | `[id].py` with `async def show(id: UUID)` → `/users/{id}`     |
| `[id]/...`       | dynamic folder                                                                          | `users/[id]/posts.py` → `/users/{id}/posts`                   |
| `[...rest].py`   | catch-all (reserved for v0.2+)                                                          | not used in v0.1 by default                                   |
| `(group)/`       | folder ignored in URL — group by team / feature / auth without changing the URL surface | `(admin)/stats.py` → `/stats`                                 |
| `_middleware.py` | wraps every route in the subtree                                                        | runs in order: app → tree → leaf                              |
| `_scope.py`      | declares request-scoped DI providers + scope-scoped lifespan hooks                      | exports `provide()` and optionally `startup()` / `shutdown()` |
| `_*.py`          | private — colocated helpers, not routed                                                 | `_db.py`, `_validators.py`                                    |

### Dot-flat style

The leaf filename is split on `.` and each piece becomes a URL segment. A trailing `index` is dropped (means "match the parent exactly").

| Pattern              | URL effect                              | Example                                                |
| -------------------- | --------------------------------------- | ------------------------------------------------------ |
| `a.b.c.py`           | nested URL segments                     | `billing.webhooks.py` → `/billing/webhooks`            |
| `$name`              | dynamic segment (parallels `[name]`)    | `users.$id.py` → `/users/{id}`                         |
| `.index`             | trailing `index` matches the parent     | `users.$id.index.py` → `/users/{id}`                   |
| `(group)`            | dotted group piece, stripped from URL   | `(admin).stats.py` → `/stats`                          |
| `$$rest`             | catch-all (reserved for v0.2+)          | not used in v0.1 by default                            |

### Mixing the two

Folder hierarchy and dotted leaf concatenate:

| Pattern                            | URL                              |
| ---------------------------------- | -------------------------------- |
| `api/v1.$version.posts.py`         | `/api/v1/{version}/posts`        |
| `(admin)/users.$id.py`             | `/users/{id}`                    |
| `users/[id]/posts.$postId.py`      | `/users/{id}/posts/{postId}`     |

`_middleware.py` and `_scope.py` are always folder-scoped — a dotted file inherits the same middleware / DI chain its folder gives every other file there.

## Composition order at request time

1. App-level middleware (registered via `plugins.py`).
2. Each `_middleware.py` from root to leaf.
3. Each `_scope.py`'s providers become available in handler `Annotated[...]` slots.
4. The handler runs.
5. Response unwinds in reverse: leaf middleware exits first, root last.

The inner-most scope wins for providers of the same name; the outer-most middleware runs first on the way in and last on the way out.

## A realistic tree

```
src/app/routes/
├── _middleware.py            # global request id + auth
├── _scope.py                 # provides db session
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
│   ├── _scope.py             # provides admin-only audit logger
│   ├── stats.py              # /stats
│   └── users.py              # /users  (separate from users/index.py)
└── billing/
    ├── _scope.py             # provides stripe client
    └── webhooks.py           # /billing/webhooks
```

## Why brackets / dollars work as filenames

Python doesn't allow `[`, `]`, or `$` in module names, so Quay loads route files via `importlib.util.spec_from_file_location()` rather than ordinary `import` statements. This is well-trodden ground — pytest, fastapi-file-router, and Django's app auto-discovery all rely on the same mechanism. The filename is just a string on disk; the import machinery never sees the dotted parts as package attribute lookups.

The trade-off: you can't write `from app.routes.users.[id] import ...` or `from app.routes.users.$id import ...`. In practice, route files almost never need to import each other; when they do, Quay provides an explicit alias mechanism.

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
from quay import Middleware
from quay.middleware import Request, Response

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

## Scopes

A `_scope.py` is the subtree's DI + lifespan declaration. It does two things:

1. Declares **request-scoped providers** via `@provide(...)`. Handlers below the file can take any provided name as an `Annotated[T, provider]` dependency.
2. Optionally exposes **scope-scoped lifespan hooks** (`startup()` / `shutdown()`) that fire when the app starts up and shuts down.

```python
# src/app/routes/users/_scope.py
from quay import provide
from app.lib.db import session_factory

@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

Providers are request-scoped: a new instance per request, cleaned up on response. Nested scopes inherit from parent scopes and can override providers by name — the inner-most wins.

`startup()` / `shutdown()` are useful for things like opening a long-lived client (search index, broker) only when a specific subtree is active, so you don't pay the cost in every process or worker.

```python
# src/app/routes/billing/_scope.py
from quay import provide
from stripe import StripeClient

_stripe: StripeClient | None = None

async def startup():
    global _stripe
    _stripe = StripeClient(api_key=settings.stripe_key.get_secret_value())

async def shutdown():
    if _stripe is not None:
        await _stripe.aclose()

@provide("stripe")
async def get_stripe() -> StripeClient:
    assert _stripe is not None
    return _stripe
```

## What the router emits

Every discovered handler becomes a route registration in the IR. From the IR you get:

- Generated TypeScript client.
- Route diagnostics page at `/__quay`.
- Snapshot tests for the route table (a single JSON fixture).
- Inputs for `quay diff` to flag breaking changes in CI.

The router is the source of truth. Nothing else writes to the IR.
