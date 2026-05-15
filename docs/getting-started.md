# Getting started

Five minutes from `uv add` to a typed handler discovered automatically by the file router.

## Requirements

| Tool   | Version | Why                                        |
| ------ | ------- | ------------------------------------------ |
| Python | ≥ 3.11  | Quay uses modern type-hint syntax.         |
| `uv`   | latest  | Python package manager. `brew install uv`. |

## 1. Install

> Quay is in **alpha**. The version pin below opts you into the
> prerelease channel; once v0.1.0 ships, drop it.

```bash
uv add 'quay==0.1.0a0'
```

## 2. Scaffold

```bash
quay new my-app
cd my-app
uv sync
```

What you get:

```
my-app/
├── pyproject.toml
├── quay.toml
├── .env / .env.example
└── src/app/
    ├── config.py
    ├── plugins.py
    ├── lifespan.py
    └── routes/
        ├── _middleware.py
        └── index.py
```

## 3. Write a handler

```python
# src/app/routes/users/[id].py
from typing import Annotated
from uuid import UUID
from msgspec import Struct
from quay import get, raises
from quay.errors import NotFound

class User(Struct):
    id: UUID
    name: str

@get
@raises(NotFound)
async def show(id: UUID) -> User:
    if id == UUID(int=0):
        raise NotFound(f"user {id}")
    return User(id=id, name="ada")
```

That's it. No `app.add_route(...)` line. The file router discovers
`src/app/routes/users/[id].py` and registers `GET /users/{id}` into the
IR.

## 4. Run dev

```bash
quay dev
```

What that does:

1. Discovers `src/app/routes/` → registers handlers → emits a typed `client.ts` for the frontend.
2. Boots uvicorn on `http://127.0.0.1:8000`.
3. Serves `/__quay` — route tree, registered tasks, current config (secrets redacted), plugin list, OTel trace tail.
4. Hot-reloads `_middleware.py` and `_scope.py` on save.

## 5. Add middleware

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

`_middleware.py` wraps every route in the subtree it lives in. Add one
under `routes/(admin)/_middleware.py` and it only applies to admin routes.

## 6. Add a scoped dependency

```python
# src/app/routes/users/_scope.py
from quay import provide
from app.lib.db import session_factory

@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

Now any handler under `routes/users/` can take `db: Annotated[Session, get_session]`.

## 7. Background tasks

```python
# src/app/tasks/emails.py
from quay import task

@task(queue="emails", retries=5, backoff="exponential")
async def send_welcome(user_id: str) -> None:
    ...
```

```python
# src/app/routes/users/index.py
from app.tasks.emails import send_welcome
from quay import post

@post
async def create(data: NewUser) -> User:
    user = await db.insert(...)
    await send_welcome.enqueue(user.id)
    return user
```

Pick an adapter in `plugins.py` (Dramatiq, Celery, Arq, in-process).
The handler doesn't change.

## Where to go next

- [Reference](./reference.md) — every primitive in one page.
- [Routing](./routing.md) — the full file-based-routing convention.
- [Plugins](./plugins.md) — installing and authoring plugins.
- [Architecture](./architecture.md) — what's happening under the hood (for contributors).
- [`examples/`](../examples) — runnable starter projects.

## Troubleshooting

**The route doesn't show up in `/__quay`.**
Make sure the file is under `src/app/routes/`, the filename is correct
(`index.py`, `foo.py`, or `[param].py`), and it doesn't start with `_`
(those are private).

**A `[id].py` segment isn't binding to my handler parameter.**
The parameter name must match the bracketed segment name exactly. `[id].py`
needs `async def show(id: ...)`, not `async def show(user_id: ...)`.

**Middleware fires in the wrong order.**
Composition order is app-level → root `_middleware.py` → ... → leaf
`_middleware.py` → handler. Response unwinds in reverse.
