# Examples

Runnable starter projects exercising the v0.1 surface. Each example is
self-contained, has its own `pyproject.toml` that pins `quay` against
the in-repo workspace via `tool.uv.sources`, and is **not** part of the
publish pipeline — they exist to demo features and catch regressions.

| Example                                 | Demonstrates                                                                                              |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| [`minimal/`](./minimal)                 | The smallest possible Quay app — one handler, zero plugins. Sanity-checks the dev loop.                   |
| [`minimal-crud/`](./minimal-crud)       | CRUD on one resource: file routing (`index.py` + `[id].py`), msgspec models, typed errors, `@raises` envelope. |
| [`blog/`](./blog)                       | The deep example. SQLAlchemy + SQLite, scoped DI, admin auth via providers, nested subtrees, background `@task` + `@cron`, lifespan + plugin startup, full test suite. |

## Running an example

```bash
cd examples/<name>
uv sync
uv run uvicorn app.app:app --reload
```

Then visit:

- `http://127.0.0.1:8000/` — handler output
- `http://127.0.0.1:8000/healthz` — liveness
- `http://127.0.0.1:8000/__quay` — diagnostics (route tree, plugins, settings)

The `blog/` example also has a pytest suite:

```bash
cd examples/blog
uv sync
uv run pytest
```
