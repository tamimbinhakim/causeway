<div align="center">

# Quay

**A lean backend framework for type-safe Python APIs. Your function signature is the API contract; the typed TypeScript client comes free.**

[![CI](https://github.com/tamimbinhakim/quay/actions/workflows/ci.yml/badge.svg)](https://github.com/tamimbinhakim/quay/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/quay.svg)](https://pypi.org/project/quay/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[**Quickstart**](./docs/getting-started.md) · [**Docs**](./docs) · [**Roadmap**](./ROADMAP.md)

</div>

## What Quay is

A backend-only, Python-native framework that contributes exactly five things to your application surface:

1. **File-based routing** — `[id].py` dynamic segments, `(group)/` route groups, `_middleware.py` / `_scope.py` per-tree composition.
2. **Typed config & DI** — `pydantic-settings` wrapper with request-scoped providers via `_scope.py`. No container boilerplate.
3. **Middleware & scope composition** — wraps every route in a subtree with one file at the root of that subtree.
4. **Background-task contract** — `@task` decorator + adapter protocol. Dramatiq ships as the reference; swap to Celery / Arq / TaskIQ with one line.
5. **Plugin registry** — entry-point discovery so `quay-auth-clerk`, `quay-storage-s3`, `quay-sqlmodel`, etc. install cleanly.

Underneath, the typed-RPC layer (IR + TS codegen + streaming) is provided by `dyadpy`, a lower-level primitive Quay depends on. From an application author's perspective it's all just Quay — you write Python handlers; Quay registers them, validates them, and emits a TypeScript client alongside the running app.

Everything outside the five things (ORM, auth, mailer, storage, cache, search, …) is a **plugin contract with reference adapters** — not in core.

## What Quay is not

- Not an ORM. (Use SQLModel / SQLAlchemy / Tortoise / your choice via the `quay-sqlmodel` plugin.)
- Not an admin panel.
- Not an HTML / template engine. The TypeScript client is generated; the frontend is yours.
- Not an infrastructure provisioner. (That's Terraform / Pulumi / Modal.)

See [`docs/design.md`](./docs/design.md) for the full philosophy and the explicit non-goals.

## 30-second example

```
my-app/
├── pyproject.toml
├── quay.toml
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
from quay import get, patch, raises
from quay.errors import NotFound

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
quay dev
```

What that does:

1. Discovers `src/app/routes/` → registers handlers → emits a typed `client.ts` for your frontend.
2. Boots uvicorn on `http://127.0.0.1:8000`.
3. Serves `/__quay` — route tree, registered tasks, current config (secrets redacted), plugin list.
4. Hot-reloads `_middleware.py` and `_scope.py` on change.

## Why you'd use it

- **Signature-as-contract.** Your handler's Python signature _is_ the wire schema. No `class CreatePostRequest(BaseModel)` mirrored in three files.
- **Project shape for free.** File-based routing, scoped DI, middleware, plugin registry — all there the moment you scaffold.
- **Plugins, not batteries.** Core ships contracts and one reference adapter each. Pick a real backend with one line in `plugins.py`.
- **Cloud-agnostic.** No provisioner, no platform lock-in. Runs anywhere ASGI runs.
- **Encore-style conventions without Encore's cloud.**

## How it compares

|                     | **Quay**          | FastAPI        | Django + Ninja | Encore.ts        | NestJS          |
| ------------------- | ----------------- | -------------- | -------------- | ---------------- | --------------- |
| Scope               | Backend framework | Router lib     | Full framework | Backend + infra  | Structural      |
| Owns ORM?           | **No**            | No             | Yes            | Declarative      | No              |
| Owns auth?          | **No** (plugins)  | No             | Yes            | Partial          | Partial         |
| File-based routing? | **Yes**           | No             | No             | No               | No              |
| Cloud lock-in?      | **None**          | None           | None           | Medium           | None            |
| Closest comparison  | —                 | Building block | Heavy alt      | Closest ambition | Structural peer |

Full positioning matrix in [`docs/design.md`](./docs/design.md).

## Install

> Quay is in **alpha** (`0.1.0a0`). The version pin opts you into the
> prerelease channel. Once v0.1.0 ships, drop the pin.

```bash
uv add 'quay==0.1.0a0'
```

## Stability

Pre-1.0. Pin exact versions. After 1.0:

- **Patch + minor never break.**
- **Major bumps follow a deprecation cycle** — one full minor of warnings before removal.
- **The plugin contract is part of the stable surface.**

Details: [`docs/semver.md`](./docs/semver.md), [`docs/ir-stability.md`](./docs/ir-stability.md), [`docs/lts.md`](./docs/lts.md).

## Packages

| Package                          | What it is                                                   | Status |
| -------------------------------- | ------------------------------------------------------------ | ------ |
| [`quay`](./packages/quay) (PyPI) | Core framework: routing, config, DI, tasks, plugin registry. | v0.1 α |

Out-of-core official plugins (planned, own repos): `quay-sqlmodel`, `quay-auth-*`, `quay-storage-s3`, `quay-mailer-resend`, `quay-deploy-modal`, `quay-deploy-fly`. Full inventory in [`ROADMAP.md`](./ROADMAP.md#plugin-ecosystem).

## Contributing

Issues that start with "I tried to use Quay for X and got confused" are the most valuable kind. Read [CONTRIBUTING.md](./CONTRIBUTING.md), be kind ([Code of Conduct](./CODE_OF_CONDUCT.md)).

## License

[MIT](./LICENSE).
