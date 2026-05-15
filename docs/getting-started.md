# Getting started

The point of this page is to get you from "I've heard of Causeway" to "I have a typed handler running and a TypeScript client falling out the other end" in about five minutes. No yak-shaving.

If you'd rather understand **why** Causeway exists before you try it, read [Why Causeway](./why-causeway.md) first — it's the warmest place to start.

## What you'll need

| Tool   | Version | Why                                        |
| ------ | ------- | ------------------------------------------ |
| Python | ≥ 3.11  | Causeway uses modern type-hint syntax. `X \| Y`, `Annotated[T, …]`, the works. |
| `uv`   | latest  | Python package manager. Way faster than pip; `brew install uv` on macOS. |

## 1. Install

> Causeway is in **alpha**. The version pin below opts you into the prerelease channel; once `v0.1.0` ships, you can drop it.

```bash
uv add 'causeway==0.1.0a0'
```

## 2. Scaffold a new app

```bash
causeway new my-app
cd my-app
uv sync
```

What you get:

```
my-app/
├── pyproject.toml
├── causeway.toml                 # framework manifest — what the TS client sees
├── .env / .env.example       # local secrets
└── src/app/
    ├── config.py             # Settings(BaseSettings) — typed config
    ├── plugins.py            # register(DramatiqAdapter(...)), etc.
    ├── lifespan.py           # optional app-level startup / shutdown
    └── routes/
        ├── _middleware.py    # wraps every route below this folder
        └── index.py          # GET /
```

Nothing in that tree is sacred — delete files you don't need, add the ones you do. The router only cares about what's under `src/app/routes/`.

## 3. Write a handler

```python
# src/app/routes/users/[id].py
from typing import Annotated
from uuid import UUID
from msgspec import Struct
from causeway import get, raises
from causeway.errors import NotFound

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

That's the whole handler. There's no `app.add_route(...)` line; no central `urls.py`. The file router finds `src/app/routes/users/[id].py`, sees the `@get`-decorated function, and registers `GET /users/{id}` into the IR. The parameter name (`id`) has to match the bracketed segment (`[id]`) — that's the convention.

Prefer the flat TanStack-style layout? Either of these works the same way:

```
src/app/routes/users.$id.py            # /users/{id}
src/app/routes/users.$id.index.py      # /users/{id} (explicit "match parent")
```

And you can mix folders and dotted leaves: `routes/api/v1.$version.posts.py` → `/api/v1/{version}/posts`. The conventions are interchangeable; pick what reads best for each route.

## 4. Run the dev loop

```bash
causeway dev
```

What that does, in one process:

1. Walks `src/app/routes/` → registers every handler → emits a typed `client.ts` ready for your frontend.
2. Boots uvicorn on `http://127.0.0.1:8000`.
3. Serves a diagnostics page at **`/__causeway`** — route tree, registered tasks, current config (secrets redacted), plugin list, OTel trace tail. Open it. It's the fastest way to know what Causeway thinks of your app.
4. Hot-reloads `_middleware.py` and `_scope.py` on save, without losing in-memory state where it can preserve it.

Hit `http://127.0.0.1:8000/users/some-uuid` to see the handler respond.

## 5. Add middleware

```python
# src/app/routes/_middleware.py
from causeway import Middleware
from causeway.middleware import Request, Response

class RequestId(Middleware):
    async def __call__(self, req: Request, call_next):
        rid = req.headers.get("x-request-id") or new_id()
        req.state.request_id = rid
        resp: Response = await call_next(req)
        resp.headers["x-request-id"] = rid
        return resp

middleware = [RequestId()]
```

`_middleware.py` wraps every route in the **subtree** it lives in. Add one under `routes/(admin)/_middleware.py` and it only applies to admin routes — the parentheses make `(admin)` a route group, so it doesn't show up in the URL.

That subtree-scoped composition is the trick that lets you avoid the "decorator stack on every handler" pattern.

## 6. Add a scoped dependency

```python
# src/app/routes/users/_scope.py
from causeway import provide
from app.lib.db import session_factory

@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

Now any handler under `routes/users/` can take `db: Annotated[Session, get_session]` and Causeway will inject a fresh, request-scoped session for each call. Nested scopes inherit and can override by name — the inner-most wins.

## 7. Background tasks

```python
# src/app/tasks/emails.py
from causeway import task

@task(queue="emails", retries=5, backoff="exponential")
async def send_welcome(user_id: str) -> None:
    ...
```

```python
# src/app/routes/users/index.py
from app.tasks.emails import send_welcome
from causeway import post

@post
async def create(data: NewUser) -> User:
    user = await db.insert(...)
    await send_welcome.enqueue(user.id)
    return user
```

In tests, swap to inline execution:

```python
from causeway.testing import tasks_eager

async def test_signup_sends_welcome(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
```

You pick the broker in `plugins.py`:

```python
# src/app/plugins.py
from causeway import register
from causeway_tasks_dramatiq import DramatiqAdapter

register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
```

Want Celery, Arq, or in-process? Replace the import and the class. The `@task` and `.enqueue(...)` code doesn't move.

## Where to go from here

- **[Routing](./routing.md)** — the full file-based-routing convention. Folder style, dot-flat style, mixing, middleware, scopes.
- **[Plugins](./plugins.md)** — installing and authoring plugins.
- **[Tasks](./tasks.md)** — the full `@task` contract and the adapter ecosystem.
- **[Reference](./reference.md)** — every primitive on one page.
- **[Internals](./internals/README.md)** — what's happening under the hood (you're contributing? start here).
- **[`examples/`](../examples)** — runnable starter projects you can poke at.

## Troubleshooting

**The route doesn't show up in `/__causeway`.**
Make sure the file is under `src/app/routes/`, the filename matches a convention (`index.py`, `foo.py`, `[param].py`, or any of the dot-flat forms), and it doesn't start with `_` (those are private — `_middleware.py` and `_scope.py` are special, anything else underscore-prefixed is colocated helper code).

**A `[id].py` segment isn't binding to my handler parameter.**
The parameter name has to match the bracketed segment name **exactly**. `[id].py` needs `async def show(id: ...)`, not `async def show(user_id: ...)`. Same rule for dot-flat: `users.$userId.py` wants `async def show(userId: ...)`.

**Middleware fires in the wrong order.**
Composition order is app-level → root `_middleware.py` → … → leaf `_middleware.py` → handler. Response unwinds in reverse. If you want a guard to run before everything, put it at the root; if you want it to be the last thing before the handler, put it at the leaf.

**My TypeScript client is empty / missing types.**
Check `causeway.toml` — the IR only emits what's exposed there. For settings, that's the `[client] expose_settings = [...]` allowlist (secrets are never exposed, even if you list them). For routes, that's everything the router discovered.

Anything else surprising or unclear? Open a [doc issue](https://github.com/tamimbinhakim/causeway/issues/new?labels=docs). "I tried to use Causeway for X and got confused" issues are the most valuable kind — they're how the docs get less confusing.
