# Defining routes

File-based routing for Python. The folder tree _is_ the route table — no `urls.py`, no `routes.ts`, no central registration.

## How it works

The router walks `src/app/routes/` at boot. Every `.py` file that isn't underscore-prefixed becomes a route file; its path on disk becomes a URL pattern; every function decorated with `@get` / `@post` / `@put` / `@patch` / `@delete` becomes a handler.

```
src/app/routes/users/$id.py     →    GET /users/{id}
                                     PATCH /users/{id}
                                     DELETE /users/{id}
```

The router emits a [`Discovered` snapshot](../reference/functions/discover.md). The Causeway `create_app` factory hands that snapshot to `causeway.App` for registration; the same snapshot drives the App Graph, diagnostics page, TS client codegen, and `causeway diff`.

## The layout

| Pattern        | URL                                      |
| -------------- | ---------------------------------------- |
| `index.py`     | the folder's URL itself                  |
| `foo.py`       | `/foo`                                   |
| `$id.py`       | `/users/{id}` (with `id` in the handler) |
| `$id/posts.py` | `/users/{id}/posts`                      |
| `(admin)/x.py` | `/x` — parens are stripped from the URL  |

Dots in route filenames are rejected. Use folders for URL structure so there is one readable convention for routes, middleware, scopes, graph metadata, and client route keys.

## Route keys

Every handler also gets a public route key:

```
<METHOD> <file path with $params and without route groups>
```

Examples:

| Source file                            | Handler | HTTP path                | Route key                    | Scopes    |
| -------------------------------------- | ------- | ------------------------ | ---------------------------- | --------- |
| `routes/users/index.py`                | `@get`  | `/users`                 | `GET /users`                 | `[]`      |
| `routes/users/$id.py`                  | `@get`  | `/users/{id}`            | `GET /users/$id`             | `[]`      |
| `routes/users/$id/screen.py`           | `@post` | `/users/{id}/screen`     | `POST /users/$id/screen`     | `[]`      |
| `routes/(org)/customers/$id/screen.py` | `@post` | `/customers/{id}/screen` | `POST /customers/$id/screen` | `["org"]` |

The HTTP path uses `{id}` because Starlette needs a runtime URL pattern. The client route key keeps `$id` because it is the file-based contract developers see in the tree.

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

The trade-off: route files with `$` in the filename cannot be imported with a normal Python import statement. In practice route files rarely need to import each other; when they do, use `_helpers.py` colocated in the same folder.

## What the router emits

Every discovered handler becomes a route registration in the IR. From the IR you get:

- The generated TypeScript client.
- The App Graph used by `causeway inspect --json` and dev-only `/__causeway/graph`.
- Route diagnostics at `/__causeway`.
- Snapshot tests of the route table (a single JSON fixture).
- Inputs for [`causeway diff`](../reference/cli/diff.md) to flag breaking changes in CI.

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
- [Route groups](./route-groups.md) — `(admin)/` for organization without changing URLs.
- [Middleware](./middleware.md) — `_middleware.py` per subtree.
- [Scopes](./scopes.md) — `_scope.py` for request-scoped DI + lifespan hooks.
