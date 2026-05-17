<div align="center">

# Causeway

**A lean backend framework for type-safe Python APIs.**
**Your function signature is the API contract; the typed TypeScript client comes free.**

[![CI](https://github.com/tamimbinhakim/causeway/actions/workflows/ci.yml/badge.svg)](https://github.com/tamimbinhakim/causeway/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/causeway.svg)](https://pypi.org/project/causeway/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[**Quickstart**](./docs/getting-started/installation.md) · [**Why Causeway**](./docs/why-causeway.md) · [**Docs**](./docs) · [**Roadmap**](./ROADMAP.md)

</div>

## Why this exists (a short story)

A while back I was working on AML (Anti-Money-Laundering) software for a client. Half the system was rules-and-graph-traversal work, and the other half — the half that actually caught the suspicious behavior — was ML models. Python was the only sane choice on the model side, so Python won the whole backend.

But I'm a React person at heart. I wanted the frontend story to feel as good as it does in Next.js or TanStack Start. So I reached for **FastAPI**, because it had the OpenAPI story going for it, and tried to make the contract flow from Python into the React app.

It mostly worked. But "mostly" is exactly where you start losing whole afternoons — the OpenAPI generators drift, the request/response shapes don't quite match what your handlers actually return, you end up writing the same `interface User` in three places. The seam between the Python types I'd just written and the TypeScript types my React app needed was always a little broken.

So I built **[dyadpy](https://github.com/tamimbinhakim/dyadpy)** — a typed-RPC primitive that walks your Python signatures into an IR and emits a TypeScript client that's exactly what the server returns. No OpenAPI middle-man, no generator drift, no manual sync.

dyadpy is the right primitive but it's deliberately low-level — it knows nothing about routing, config, DI, background jobs, middleware, or plugins. I needed a layer on top that would let me ship a real backend without writing the same scaffolding for the tenth time.

That layer is **Causeway.**

## What Causeway is

A backend-only, Python-native framework that contributes exactly five things to your application surface:

1. **File-based routing** — `[id].py` / `$id` dynamic segments, `(group)/` route groups, `_middleware.py` / `_scope.py` per-tree composition. See [`docs/building/routing/`](./docs/building/routing/defining-routes.md).
2. **Typed config & DI** — a `pydantic-settings` wrapper with request-scoped providers. No DI container boilerplate.
3. **Middleware & scope composition** — one file at the root of a subtree wraps every route below it.
4. **Background-task contract** — `@task` decorator + adapter protocol. Dramatiq ships as the reference; swap to Celery / Arq / TaskIQ with one line.
5. **Plugin registry** — entry-point discovery so `causeway-auth-jwt`, `causeway-storage-s3`, `causeway-db-sqlmodel`, etc. install cleanly.

Underneath, the typed-RPC layer (IR + TS codegen + streaming) is provided by [`dyadpy`](https://github.com/tamimbinhakim/dyadpy). From an application author's perspective it's all just Causeway — you write Python handlers; Causeway registers them, validates them, and emits a TypeScript client alongside the running app.

Everything outside those five things (ORM, auth, mailer, storage, cache, search, …) is a **plugin contract with reference adapters** — not in core.

## What Causeway is not

- Not an ORM. Use SQLModel / SQLAlchemy / Tortoise / your choice via the `causeway-db-sqlmodel` plugin.
- Not an admin panel.
- Not an HTML / template engine. The TypeScript client is generated; the frontend is yours.
- Not an infrastructure provisioner. That's Terraform / Pulumi / Modal.

The full design philosophy and the explicit non-goals live in [`docs/why-causeway.md`](./docs/why-causeway.md).

## 30-second example

```
my-app/
├── pyproject.toml
├── causeway.toml
└── src/app/
    ├── config.py            # Settings(BaseSettings)
    ├── plugins.py           # register(DramatiqAdapter(...))
    └── routes/
        ├── _middleware.py
        ├── index.py         # /
        └── users/
            ├── _scope.py    # provides db session
            ├── index.py     # /users
            └── [id].py      # /users/{id}
```

```python
# src/app/routes/users/[id].py
from typing import Annotated
from uuid import UUID
from msgspec import Struct
from causeway import get, patch, raises
from causeway.errors import NotFound

class User(Struct):
    id: UUID
    name: str
    email: str

@get
@raises(NotFound)
async def show(id: UUID, db: Annotated[Session, get_session]) -> User:
    user = await db.get(User, id)
    if user is None:
        raise NotFound(f"user {id}")
    return user
```

```bash
causeway dev
```

What that does:

1. Discovers `src/app/routes/` → registers handlers → emits a typed `client.ts` for your frontend.
2. Boots uvicorn on `http://127.0.0.1:8000`.
3. Serves `/__causeway` — route tree, registered tasks, current config (secrets redacted), plugin list.
4. Hot-reloads `_middleware.py` and `_scope.py` on change.

Prefer the TanStack-Router-style flat layout? Same routes, dot-flat:

```
src/app/routes/
├── index.py
├── users.index.py            # /users
└── users.$id.py              # /users/{id}
```

You can mix the two freely in the same tree. Details: [`docs/building/routing/`](./docs/building/routing/defining-routes.md).

## Why you'd use it

- **Signature-as-contract.** Your handler's Python signature _is_ the wire schema. No `class CreatePostRequest(BaseModel)` mirrored in three files.
- **Project shape for free.** File-based routing, scoped DI, middleware, plugin registry — all there the moment you scaffold.
- **Plugins, not batteries.** Core ships contracts and one reference adapter each. Pick a real backend with one line in `plugins.py`.
- **Cloud-agnostic.** No provisioner, no platform lock-in. Runs anywhere ASGI runs.
- **Encore-style conventions without Encore's cloud.**

## How it compares

|                     | **Causeway**          | FastAPI        | Django + Ninja | Encore.ts        | NestJS          |
| ------------------- | ----------------- | -------------- | -------------- | ---------------- | --------------- |
| Scope               | Backend framework | Router lib     | Full framework | Backend + infra  | Structural      |
| Owns ORM?           | **No**            | No             | Yes            | Declarative      | No              |
| Owns auth?          | **No** (plugins)  | No             | Yes            | Partial          | Partial         |
| File-based routing? | **Yes**           | No             | No             | No               | No              |
| Cloud lock-in?      | **None**          | None           | None           | Medium           | None            |
| Closest comparison  | —                 | Building block | Heavy alt      | Closest ambition | Structural peer |

Full positioning matrix and the trade-offs in [`docs/why-causeway.md`](./docs/why-causeway.md).

## Install

> Causeway is in **alpha** (`0.1.0a0`). The version pin opts you into the
> prerelease channel. Once v0.1.0 ships, drop the pin.

```bash
uv add 'causeway==0.1.0a0'
```

## Stability

Pre-1.0. Pin exact versions. After 1.0:

- **Patch + minor never break.**
- **Major bumps follow a deprecation cycle** — one full minor of warnings before removal.
- **The plugin contract is part of the stable surface.**

Details in [`docs/stability/`](./docs/stability) — semver, IR stability, LTS.

## Packages

| Package                          | What it is                                                   | Status |
| -------------------------------- | ------------------------------------------------------------ | ------ |
| [`causeway`](./packages/causeway) (PyPI) | Core framework: routing, config, DI, tasks, plugin registry. | v0.1 α |

The official plugin set (`causeway-tasks-dramatiq`, `causeway-storage-s3`, `causeway-auth-jwt`, `causeway-db-sqlmodel`, etc.) lives under [`packages/`](./packages). Full inventory and roadmap in [`ROADMAP.md`](./ROADMAP.md#plugin-ecosystem).

## Contributing

Issues that start with "I tried to use Causeway for X and got confused" are the most valuable kind. Skim [CONTRIBUTING.md](./CONTRIBUTING.md) for the on-ramp, and if you're going deep, [`docs/internals/`](./docs/internals) is the contributor's tour of the codebase.

## License

[MIT](./LICENSE).
