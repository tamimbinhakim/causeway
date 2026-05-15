# quay (Python)

> A lean backend framework for type-safe Python APIs.

```bash
uv add 'quay==0.1.0a0'   # alpha — drop the pin once v0.1.0 ships
```

This is the core Python package of [Quay](https://github.com/tamimbinhakim/quay). It ships:

- A **file-based router** that walks `src/app/routes/**/*.py`, picks up `[id].py`, `(group)/`, `_middleware.py`, and `_scope.py`, and registers handlers into the app's route table.
- A **typed config layer** that wraps `pydantic-settings` and exposes non-secret fields to the generated TypeScript client.
- A **scoped DI container** driven by `_scope.py` providers.
- A **`@task` contract** for background jobs with a Dramatiq reference adapter.
- A **plugin registry** with Python-entry-point discovery and per-environment activation.
- A **CLI** (`quay new`, `quay dev`, `quay build`, `quay deploy <target>`) that runs the whole loop.

For the full story, the design rationale, and a side-by-side vs. FastAPI / Django + Ninja / Encore.ts / NestJS, see the [repo README](https://github.com/tamimbinhakim/quay).

## 30-second example

```
my-app/
├── pyproject.toml
├── quay.toml
└── src/app/
    ├── config.py
    ├── plugins.py
    └── routes/
        ├── _middleware.py
        ├── index.py
        └── users/
            ├── _scope.py
            ├── index.py
            └── [id].py
```

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
    ...
```

Run it:

```bash
quay dev
```

`quay dev` discovers the routes, boots uvicorn, regenerates a typed `client.ts` for your frontend on every save, and exposes `/__quay` with the route tree, registered tasks, current config, and plugin list.

## Primitives in this package

| Primitive                                        | Purpose                                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------ |
| File router (`[id].py`, `(group)/`)              | Discovery + URL pattern generation.                                      |
| `_middleware.py` / `_scope.py`                   | Per-subtree middleware + scoped DI providers.                            |
| `Settings` (wraps `pydantic-settings`)           | Typed config with allowlisted exposure to the generated client.          |
| `@get` / `@post` / `@put` / `@patch` / `@delete` | HTTP method decorators.                                                  |
| `@task(...)`                                     | Background-job contract; adapter-agnostic.                               |
| `@cron(...)`                                     | Scheduled tasks via the same adapter.                                    |
| `register(...)`                                  | Plugin registration (`TaskAdapter`, `Storage`, `KV`, `AuthProvider`, …). |
| `TestApp`                                        | Test client with DI overrides and `tasks_eager()` mode.                  |
| `quay` CLI                                       | `new`, `dev`, `build`, `plugins`, `deploy <target>`.                     |

Full reference: <https://github.com/tamimbinhakim/quay/blob/main/docs/reference.md>

## Optional extras

```bash
uv add 'quay[dramatiq]'  # reference task adapter
uv add 'quay[otel]'      # OpenTelemetry middleware hooks
uv add 'quay[all]'       # everything
```

## Scope

Quay ships project shape and a small set of contracts. It does **not** ship vertical integrations — no ORM, no admin panel, no template engine, no infrastructure provisioning, no AI / LLM helpers. Those layers compose on top of the fundamentals and live in their own plugin packages or in user code.

## License

MIT
