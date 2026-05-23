# Defining routes

File-based routing for Python. The folder tree _is_ the route table — no `urls.py`, no `routes.ts`, no central registration.

## How it works

The router walks `src/app/routes/` at boot. Every `.py` file that isn't underscore-prefixed becomes a route file; its path on disk becomes a URL pattern; every function decorated with `@get` / `@post` / `@put` / `@patch` / `@delete` becomes a handler.

```
src/app/routes/users/$id.py     →    GET /users/{id}
                                     PATCH /users/{id}
                                     DELETE /users/{id}
```

The router emits a [`Discovered` snapshot](../../api-reference/functions/discover.md). The Causeway `create_app` factory hands that snapshot to `dyadpy.App` for registration; the same snapshot drives the diagnostics page, the TS client codegen, and `causeway diff`.

## The two layouts

Causeway accepts both folder hierarchy and TanStack-style dotted leaves in the same tree.

### Folder style

| Pattern        | URL                                      |
| -------------- | ---------------------------------------- |
| `index.py`     | the folder's URL itself                  |
| `foo.py`       | `/foo`                                   |
| `$id.py`       | `/users/{id}` (with `id` in the handler) |
| `$id/posts.py` | `/users/{id}/posts`                      |
| `(admin)/x.py` | `/x` — parens are stripped from the URL  |

### Dot-flat style

The leaf filename is split on `.` and each piece becomes a URL segment. A trailing `index` is dropped (means "match parent exactly").

| Pattern               | URL                 |
| --------------------- | ------------------- |
| `billing.webhooks.py` | `/billing/webhooks` |
| `users.$id.py`        | `/users/{id}`       |
| `users.$id.index.py`  | `/users/{id}`       |
| `(admin).stats.py`    | `/stats`            |

### Mixing them

Folder hierarchy and dotted leaf concatenate:

```
src/app/routes/api/v1.$version.posts.py    →    /api/v1/{version}/posts
src/app/routes/(admin)/users.$id.py        →    /users/{id}
```

`_middleware.py` and `_scope.py` are always folder-scoped — a dotted file inherits whatever its folder gives every other file there.

> **Good to know.** Folders read better for deep, group-heavy trees. Dot-flat reads better for shallow, parameter-light endpoints. You don't have to commit to one.

## What goes in a route file

```python
# src/app/routes/users/$id.py
from uuid import UUID
from msgspec import Struct
from causeway import get, patch, delete, raises
from causeway.errors import NotFound


class User(Struct):
    id: UUID
    name: str


class UserPatch(Struct):
    name: str | None = None


@get
@raises(NotFound)
async def show(id: UUID) -> User: ...


@patch
async def update(id: UUID, data: UserPatch) -> User: ...


@delete
async def remove(id: UUID) -> None: ...
```

Three rules:

1. **One method per decorator.** Decorating a function with both `@get` and `@post` is a `TypeError` at import time.
2. **Method conflicts caught at boot.** Two `@get`s for the same path raise on `causeway dev`, not at request time.
3. **The `$` segment binds by name.** `$id.py` requires the handler to take `id` (not `user_id`, not `pk`).

## Why `$` filenames work

Python doesn't allow `$` in module names, so Causeway loads route files via `importlib.util.spec_from_file_location()` rather than ordinary `import` statements. The filename is just a string on disk; the import machinery never sees `$` as an attribute lookup.

The trade-off: you can't write `from app.routes.users.$id import ...`. In practice route files rarely need to import each other; when they do, use `_helpers.py` colocated in the same folder.

## What the router emits

Every discovered handler becomes a route registration in the IR. From the IR you get:

- The generated TypeScript client.
- Route diagnostics at `/__causeway`.
- Snapshot tests of the route table (a single JSON fixture).
- Inputs for [`causeway diff`](../../api-reference/cli/diff.md) to flag breaking changes in CI.

The router is the source of truth. Nothing else writes to the IR.

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
│   ├── $id.py                # /users/{id}
│   └── $id/
│       └── posts.py          # /users/{id}/posts
├── (admin)/                  # route group (not in URL)
│   ├── _middleware.py        # require_admin guard
│   ├── _scope.py             # admin-only audit logger
│   ├── stats.py              # /stats
│   └── users.py              # /users  (separate from users/index.py)
└── billing/
    ├── _scope.py             # provides stripe client
    └── webhooks.py           # /billing/webhooks
```

## Next

- [Dynamic segments](./dynamic-segments.md) — `$id` type binding.
- [Route groups](./route-groups.md) — `(admin)/` and `(group).x.py` for organization.
- [Middleware](./middleware.md) — `_middleware.py` per subtree.
- [Scopes](./scopes.md) — `_scope.py` for request-scoped DI + lifespan hooks.
