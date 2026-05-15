<div align="center">

# Quay

**Backend conventions for type-safe Python APIs. A lean backend framework built on top of [Dyadpy](https://github.com/tamimbinhakim/dyadpy).**

[![CI](https://github.com/tamimbinhakim/quay/actions/workflows/ci.yml/badge.svg)](https://github.com/tamimbinhakim/quay/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/quay.svg)](https://pypi.org/project/quay/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

[**Quickstart**](./docs/getting-started.md) · [**Docs**](./docs) · [**Roadmap**](./ROADMAP.md)

</div>

## What Quay is

A backend-only, Python-native framework that sits on top of [Dyadpy](https://github.com/tamimbinhakim/dyadpy) (the wire-level RPC layer) and contributes exactly five things to the application surface:

1. **File-based routing** — Next.js-style `[id].py` dynamic segments, `(group)/` route groups, `_middleware.py` / `_layout.py` per-tree composition.
2. **Typed config & DI** — `pydantic-settings` wrapper with scoped providers via `_layout.py`. No container boilerplate.
3. **Middleware & layout composition** — wraps every route in a subtree with one file at the root of that subtree.
4. **Background-task contract** — `@task` decorator + adapter protocol. Dramatiq ships as the reference; swap to Celery/Arq/TaskIQ with one line.
5. **Plugin registry** — entry-point discovery so `quay-auth-clerk`, `quay-storage-s3`, `quay-sqlmodel`, etc. install cleanly.

Everything else (ORM, auth, mailer, storage) is a **plugin contract with reference adapters** — not in core.

## What Quay is not

- Not an ORM. (Use SQLModel / SQLAlchemy / Tortoise / your choice via the `quay-sqlmodel` plugin.)
- Not an admin panel.
- Not an HTML / template engine. The TS client is Dyadpy's job; the frontend is yours.
- Not an infrastructure provisioner. (That's Terraform / Pulumi / Modal.)
- **Not an AI / agent framework.** No `quay.ai` module, no LLM-specific types, no built-in vector stores. Quay stays at the structural / wire level; LLM tooling is user code or a separate library (LangGraph / Pydantic AI / Mastra).

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
            ├── _layout.py   # provides db session
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

1. Discovers `src/app/routes/` → registers handlers into Dyadpy → triggers TS client regeneration.
2. Boots uvicorn on `http://127.0.0.1:8000`.
3. Serves `/__quay` — route tree, registered tasks, current config (secrets redacted).
4. Hot-reloads `_middleware.py` and `_layout.py` on change.

## Why you'd use it

- **You like the Dyadpy contract** (function signature = API contract) but want project shape for free.
- **You want Encore-style conventions** without Encore's cloud lock-in.
- **You want Next.js-style routing** in Python.
- **You want plugins, not batteries.** Core ships contracts and one reference adapter each.

## How it compares

|                     | **Quay**                | FastAPI        | Django + Ninja | Encore.ts        | NestJS          |
| ------------------- | ----------------------- | -------------- | -------------- | ---------------- | --------------- |
| Scope               | Backend framework       | Router lib     | Full framework | Backend + infra  | Structural      |
| Owns ORM?           | **No**                  | No             | Yes            | Declarative      | No              |
| Owns auth?          | **No** (plugins)        | No             | Yes            | Partial          | Partial         |
| File-based routing? | **Yes (Next.js style)** | No             | No             | No               | No              |
| Cloud lock-in?      | **None**                | None           | None           | Medium           | None            |
| Closest comparison  | —                       | Building block | Heavy alt      | Closest ambition | Structural peer |

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

Out-of-core official plugins (planned, own repos): `quay-sqlmodel`, `quay-auth-*`, `quay-storage-s3`, `quay-mailer-resend`, `quay-deploy-modal`, `quay-deploy-fly`.

See [`ROADMAP.md`](./ROADMAP.md).

## Contributing

Issues that start with "I tried to use Quay for X and got confused" are the most valuable kind. Read [CONTRIBUTING.md](./CONTRIBUTING.md), be kind ([Code of Conduct](./CODE_OF_CONDUCT.md)).

## License

[MIT](./LICENSE).
