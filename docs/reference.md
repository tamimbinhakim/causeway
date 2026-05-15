# Reference

Every primitive in one page. This is the page you keep open in a tab.

> **Status:** v0.1 alpha. APIs may shift before 1.0. Pin exact versions.

## Routing

### File conventions

| Pattern          | URL effect                                                    | Example                                                       |
| ---------------- | ------------------------------------------------------------- | ------------------------------------------------------------- |
| `index.py`       | the folder's URL itself                                       | `users/index.py` → `/users`                                   |
| `foo.py`         | `/foo`                                                        | `health.py` → `/health`                                       |
| `[id].py`        | dynamic segment, typed via the handler signature              | `[id].py` with `id: UUID`                                     |
| `[id]/...`       | dynamic folder                                                | `users/[id]/posts.py`                                         |
| `[...rest].py`   | catch-all (reserved; not used in v0.1 by default)             | reserved                                                      |
| `(group)/`       | folder ignored in URL — group routes by team / feature / auth | `(admin)/stats.py` → `/stats`                                 |
| `_middleware.py` | wraps every route in the subtree                              | runs in order: app → tree → leaf                              |
| `_scope.py`      | scoped dependencies + lifespan hooks for the subtree          | exports `provide()` and optionally `startup()` / `shutdown()` |
| `_*.py`          | private, not routed                                           | for colocated helpers                                         |

### Method decorators

```python
from quay import get, post, put, patch, delete

@get
async def show(id: UUID) -> User: ...

@patch
async def update(id: UUID, data: UserPatch) -> User: ...
```

All handlers in the same file share the same path; method conflicts are caught at boot.

### Param binding

Bracketed segments bind by **name**: `[id].py` requires the handler to take `id`.

### Typed errors

```python
from quay import raises
from quay.errors import NotFound

@get
@raises(NotFound)
async def show(id: UUID) -> User: ...
```

`@raises(NotFound)` becomes a discriminated union in the generated TypeScript client — the caller is forced to handle the named error case.

### Streaming

```python
from quay import get, stream

@get
async def watch(thread_id: str) -> stream[Event]: ...
```

A `stream[T]` return becomes typed SSE on the wire and an `AsyncIterable<T>` on the client.

## Middleware

```python
# src/app/routes/_middleware.py
from quay import Middleware
from quay.middleware import Request, Response

class RequestId(Middleware):
    async def __call__(self, req: Request, call_next):
        ...

middleware = [RequestId()]
```

Guards (lightweight, function-style):

```python
from quay import guard

@guard
async def require_admin(req): ...

middleware = [require_admin]
```

## Scopes

```python
# src/app/routes/users/_scope.py
from quay import provide

@provide("db")
async def get_session():
    async with session_factory() as s:
        yield s
```

Handlers under `routes/users/` can now take `db: Annotated[Session, get_session]`.

## Config

```python
# src/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    env: str = "dev"
    database_url: SecretStr
    feature_flags: dict[str, bool] = {}

settings = Settings()
```

```toml
# quay.toml
[client]
expose_settings = ["env", "feature_flags"]   # secrets never exposed
```

## Background tasks

```python
from quay import task

@task(queue="emails", retries=5, backoff="exponential")
async def send_welcome(user_id: str) -> None: ...
```

```python
await send_welcome.enqueue(user_id)
```

Cron:

```python
from quay import cron

@cron("0 * * * *")
async def hourly() -> None:
    await refresh_embeddings.enqueue()
```

Adapter swap (one line):

```python
# src/app/plugins.py
from quay import register
from quay_tasks_dramatiq import DramatiqAdapter

register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
```

## Plugin registration

```python
# src/app/plugins.py
from quay import register
from quay_tasks_dramatiq import DramatiqAdapter
from quay_storage_s3 import S3Storage
from app.config import settings

register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
register(S3Storage(bucket="uploads"))
```

Entry-point discovery is automatic for any installed package that exposes a `quay.plugins` entry point.

## Health endpoints

`GET /healthz` — process up.
`GET /readyz` — all registered plugins ready (DB connected, broker reachable, etc.).

Both are built in; override by adding `routes/healthz.py` / `routes/readyz.py`.

## Observability

```python
# any handler — automatic
# every request has a request id, span, and structured log line
```

Quay ships OTel auto-instrumentation hooks; pick your exporter via env (SigNoz, Tempo, Honeycomb, Datadog).

## Testing

```python
import pytest
from quay.testing import TestApp, tasks_eager

@pytest.fixture
async def app():
    return TestApp.from_routes("src/app/routes")

async def test_create_user(app):
    async with app.override(get_session, fake_session):
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201

async def test_task_runs_inline(app):
    async with tasks_eager():
        r = await app.post("/users", json={"name": "ada"})
    assert r.status_code == 201
```

`tasks_eager()` is part of the `TaskAdapter` contract; every adapter must support it. Inside the block, `.enqueue(...)` runs the task body in-process so the test can assert on its side-effects synchronously.

## CLI

| Command                | What it does                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| `quay new <name>`      | Scaffold a new app — `pyproject.toml`, `quay.toml`, `src/app/`, sensible defaults.                |
| `quay dev`             | Boot uvicorn + watcher + TypeScript client codegen + `/__quay` diagnostics page.                  |
| `quay build`           | Emit the IR, the generated `client.ts`, and a deployable wheel.                                   |
| `quay deploy <target>` | Invoke the relevant deploy plugin (`quay-deploy-docker`, `quay-deploy-fly`, `quay-deploy-modal`).  |
| `quay diff <a> <b>`    | Compare two IR snapshots and flag breaking changes (delegates to `dyadpy diff`).                  |
| `quay plugins`         | List currently-registered plugin adapters.                                                        |
| `quay plugin new <n>`  | Scaffold a new Quay plugin package.                                                               |
| `quay --version`       | Print the installed version.                                                                      |
