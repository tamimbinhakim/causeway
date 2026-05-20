# Plugins

Causeway is plugins-not-batteries by design. Everything Causeway deliberately doesn't ship — ORMs, auth, storage, mail, caches, search, rate limiting, payments, observability, deploy targets — lives behind a **contract** in `causeway.contracts`, with one or more reference adapters as separate packages.

## The shape of a plugin

A plugin is a Python package that:

1. **Implements one or more contracts** declared in `causeway.contracts`.
2. **Exposes a `plugin(settings)` callable** as a `causeway.plugins` entry point.
3. **Declares the contract version** it targets.

That's the whole surface a plugin author has to learn.

## Two installation paths

### Entry points (automatic)

Any installed package that declares a `causeway.plugins` entry point auto-loads at startup:

```toml
# causeway-storage-s3/pyproject.toml
[project.entry-points."causeway.plugins"]
storage-s3 = "causeway_storage_s3:plugin"
```

```python
# causeway_storage_s3/__init__.py
from causeway import register
from .store import S3Storage

def plugin(settings):
    register(S3Storage(bucket=settings.s3_bucket))
```

Install (`uv add causeway-storage-s3`) and it works. No explicit wiring needed.

### Explicit `register()` (when you need args or ordering)

```python
# src/app/plugins.py
from causeway import register, env
from causeway_tasks_dramatiq import DramatiqAdapter
from causeway_storage_s3 import S3Storage
from causeway_observe_sentry import SentryObserver
from app.config import settings


if env() == "prod":
    register(SentryObserver(dsn=settings.sentry_dsn.get_secret_value()))   # first → wraps everything
    register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
    register(S3Storage(bucket="uploads"))
```

`plugins.py` runs once when `create_app()` builds the app, after `config.py` is loaded. Registration order is preserved; later registrations override earlier ones for the same contract slot. The app factory starts plugins during ASGI lifespan startup and shuts them down in reverse order during ASGI shutdown.

## Built-in contracts

Each contract ships with a reference adapter in core (`causeway.adapters`) or in a sibling package. Picking a real backend is a one-line swap.

| Contract       | Method surface                                             | Reference                         |
| -------------- | ---------------------------------------------------------- | --------------------------------- |
| `TaskAdapter`  | `enqueue`, `schedule`, `cron`, `eager`, `status`, `result` | `causeway.tasks.InMemoryAdapter`  |
| `Storage`      | `put`, `get`, `delete`, `signed_url`, `list`               | `causeway.adapters.LocalStorage`  |
| `KV`           | `get`, `set` (TTL), `delete`, `incr`, `expire`             | `causeway.adapters.MemoryKV`      |
| `SessionStore` | `read`, `write`, `destroy`, `rotate`                       | `causeway.adapters.CookieStore`   |
| `Mailer`       | `send`, `send_template`, `verify_address`                  | bring your own                    |
| `Searchable`   | `index`, `search`, `delete`, `bulk_index`                  | bring your own                    |
| `RateLimiter`  | `acquire`, `peek`, `reset`                                 | `causeway.adapters.MemoryLimiter` |
| `FeatureFlags` | `is_on`, `variant`, `refresh`                              | `causeway.adapters.StaticFlags`   |
| `MetricsSink`  | `counter`, `gauge`, `histogram`, `timer`                   | none                              |
| `LogSink`      | `emit(record)`                                             | stdout via `structlog`            |
| `PubSub`       | `publish`, `subscribe`                                     | none                              |
| `AuthProvider` | `current_user`, `login`, `logout`, `verify`                | bring your own                    |
| `DBSession`    | `session`, `transaction`, `health`                         | provided by ORM plugins           |
| `BlobScanner`  | `scan(stream)` — virus / type checks                       | none                              |
| `DeployTarget` | `manifest`, `package`, `push(target)`                      | provided by deploy plugins        |

Contract types live in `causeway.contracts`. All are `typing.Protocol`s — duck-typed.

## Lifecycle

Every plugin observes the same lifecycle:

1. **Discovered.** `create_app()` scans entry points, then imports sibling `plugins.py` if present.
2. **Validated.** Its declared `contract_version` is checked; warnings on mismatch.
3. **Started.** `plugin.startup(settings)` runs. DB pools open, brokers connect.
4. **Ready.** `plugin.ready()` returns True. `/readyz` aggregates across all plugins.
5. **Shutdown.** Reverse registration order. First-registered shuts down last.

```python
from typing import ClassVar

class S3Storage:
    contract_version: ClassVar[str] = "v1.0"

    def __init__(self, bucket: str): ...

    async def startup(self, settings) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool: ...

    # Storage contract methods
    async def put(self, key: str, body: bytes, *, content_type=None) -> None: ...
    # ...
```

## Plugin dependencies

A plugin can declare it depends on another contract being present:

```python
class StripeBilling:
    contract_version = "v1.0"
    requires = ["DBSession", "KV"]   # registered before startup
```

If a required contract has no registered adapter at startup, Causeway refuses to boot with `plugin X requires Y, none registered`.

## Per-environment activation

```python
from causeway import register, env
from app.config import settings

if env() == "prod":
    register(SentryObserver(dsn=settings.sentry_dsn.get_secret_value()))
    register(S3Storage(bucket=settings.s3_bucket))
else:
    register(LocalStorage(path="./tmp/uploads"))
```

The `env()` helper reads `CAUSEWAY_ENV`, falls back to `ENV`, defaults to `"dev"`.

## Diagnostics

```bash
$ causeway plugins
                       Registered plugins
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Adapter          ┃ Contract version  ┃ Module               ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ DramatiqAdapter  │ v1.0              │ causeway_tasks_dramatiq  │
│ S3Storage        │ v1.0              │ causeway_storage_s3      │
│ RedisCache       │ v1.0              │ causeway_cache_redis     │
│ SmtpMailer       │ v1.0              │ causeway_mailer_smtp     │
└──────────────────┴───────────────────┴──────────────────────┘
```

Same view at `http://localhost:8000/__causeway` while `causeway dev` is running. `/readyz` returns 503 with a per-plugin status JSON until every plugin's `ready()` returns true.

## Naming convention

Official plugins use `causeway-<role>-<impl>`. The current shipping set:

- **tasks**: `causeway-tasks-dramatiq`
- **storage**: `causeway-storage-fs`, `causeway-storage-s3`
- **cache**: `causeway-cache-redis`
- **auth**: `causeway-auth-jwt`
- **mailer**: `causeway-mailer-smtp`
- **observe**: `causeway-observe-sentry`
- **flags**: `causeway-flags-growthbook`
- **db**: `causeway-db-sqlmodel`
- **deploy**: `causeway-deploy-docker`, `causeway-deploy-fly`, `causeway-deploy-modal`

Third-party plugins should use `causeway-contrib-<thing>` to avoid implying official status.

## Authoring a plugin

See [Writing a new plugin](./authoring.md).

## Contract stability

The plugin contract is part of the stable surface. After 1.0:

- Adding optional methods to a contract is non-breaking.
- Adding a new contract is non-breaking.
- Removing or renaming a method is **breaking** and follows the deprecation cycle in [`semver`](../../stability/semver.md): one full minor of `DeprecationWarning` before removal.

A plugin that targets Causeway `1.x` keeps working through every `1.y` release.

## Next

- [Writing a new plugin](./authoring.md)
- [Reference — `register`](../../api-reference/functions/register.md)
- [Reference — `env`](../../api-reference/functions/env.md)
- [Reference — contracts](../../api-reference/classes/contracts.md)
