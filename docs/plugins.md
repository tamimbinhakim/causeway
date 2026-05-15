# Plugins

Causeway is plugins-not-batteries by design. The plugin system **is** the framework's surface for everything Causeway deliberately doesn't ship: ORMs, auth, storage, mail, caches, search, rate limiting, payments, observability, deploy targets — all of it.

This page describes the contracts, the lifecycle, the registry, and how to author one.

## The shape of a plugin

A plugin is a Python package that:

1. **Implements one or more contracts.** Contracts are `typing.Protocol`s declared in `causeway.contracts`. A single package may implement several (e.g. a plugin that provides both `Storage` and `Mailer`).
2. **Exposes a `plugin(settings)` callable** as the `causeway.plugins` entry point. Causeway calls this once at startup with the validated `Settings` object, and the callable registers its adapters via `causeway.register(...)`.
3. **Declares its supported Causeway contract versions** in `pyproject.toml` so the registry can warn when a plugin targets an older protocol.

That's the entire surface a plugin author has to learn.

## Built-in contracts

Each contract ships with a reference adapter in core (or in a sibling repo for plugins that need a real dependency). Picking a real backend is a one-line swap in `plugins.py`.

| Contract       | Method surface (sketch)                                               | Reference impl                    |
| -------------- | --------------------------------------------------------------------- | --------------------------------- |
| `TaskAdapter`  | `enqueue`, `schedule`, `cron`, `eager` (test ctx), `status`, `result` | `causeway.tasks.InMemoryAdapter`      |
| `Storage`      | `put`, `get`, `delete`, `signed_url`, `list`                          | `causeway.storage.LocalStorage`       |
| `KV`           | `get`, `set` (with TTL), `delete`, `incr`, `expire`                   | `causeway.kv.MemoryKV`                |
| `SessionStore` | `read`, `write`, `destroy`, `rotate`                                  | `causeway.sessions.CookieStore`       |
| `Mailer`       | `send(to, subject, body, ...)`, `send_template`, `verify_address`     | none — bring your own             |
| `Searchable`   | `index`, `search`, `delete`, `bulk_index`                             | none — bring your own             |
| `RateLimiter`  | `acquire(key, cost=1)`, `peek`, `reset`                               | `causeway.ratelimit.MemoryLimiter`    |
| `FeatureFlags` | `is_on(flag, user=None)`, `variant`, `refresh`                        | `causeway.flags.StaticFlags`          |
| `MetricsSink`  | `counter`, `gauge`, `histogram`, `timer`                              | `causeway.metrics.NullSink`           |
| `LogSink`      | `emit(record)` — receives structured log records for forwarding       | stdout via `structlog`            |
| `PubSub`       | `publish(topic, payload)`, `subscribe(topic, handler)`                | `causeway.pubsub.MemoryBus`           |
| `AuthProvider` | `current_user(req)`, `login(creds)`, `logout(req)`, `verify(token)`   | none — bring your own             |
| `DBSession`    | `session()` (request-scoped), `transaction()`, `health()`             | none — provided by ORM plugins    |
| `BlobScanner`  | `scan(stream)` for incoming-file virus / type checks                  | `causeway.scanner.NullScanner`        |
| `DeployTarget` | `manifest()`, `package()`, `push(target)`                             | none — provided by deploy plugins |

Contracts are versioned. `causeway.contracts.v1.Storage` is the stable surface; new optional methods land in minor releases (`v1.1`), breaking changes wait for `v2`. See [`semver.md`](./stability/semver.md) for the rules.

## Two discovery paths

### Entry points (automatic)

Any installed package that declares a `causeway.plugins` entry point is auto-loaded at startup:

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

Install it (`uv add causeway-storage-s3`) and it works. No explicit wiring needed.

### Explicit `register()` (when you need args or ordering)

```python
# src/app/plugins.py
from causeway import register
from causeway_tasks_dramatiq import DramatiqAdapter
from causeway_storage_s3 import S3Storage
from causeway_observe_sentry import SentryObserver
from app.config import settings

register(SentryObserver(dsn=settings.sentry_dsn.get_secret_value()))   # first — wraps everything else
register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
register(S3Storage(bucket="uploads"))
```

`plugins.py` runs once at startup, after `config.py` is loaded. Registration order is preserved; later registrations override earlier ones for the same contract slot.

## Lifecycle

A plugin goes through four phases:

1. **Discovered.** Entry-point scan picks it up, or `register()` is called.
2. **Validated.** Its declared contract version is checked against the loaded Causeway version. Incompatible plugins fail fast with a clear error.
3. **Started.** Causeway calls `plugin.startup(settings)` if defined. This is where DB pools open, brokers connect, etc.
4. **Ready.** Causeway polls `plugin.ready()` until it returns `True`. `/readyz` returns 503 until every registered plugin is ready.

Shutdown happens in **reverse registration order**: the first-registered plugin shuts down last.

```python
class TaskAdapter(Protocol):
    contract_version: ClassVar[str]  # e.g. "v1.0"

    async def startup(self, settings: Settings) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool: ...

    async def enqueue(self, task: TaskRef, payload: bytes) -> str: ...
    # ...
```

## Configuration

Plugins read their config from the app's `Settings` (or from kwargs passed to `register(...)`). Two conventions:

- **Auto-load plugins** read from `Settings` by attribute name. A plugin that needs `redis_url` will look for `settings.redis_url` and emit a friendly error if it's missing.
- **Explicit register** plugins take whatever you pass. This is the escape hatch for non-standard names, per-env switches, or test doubles.

A plugin may declare a Pydantic settings _fragment_ that contributes fields to the app's `Settings`. The fragment is loaded with the rest of `Settings`, so env vars and `.env` work uniformly.

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
│ SQLModelSession  │ v1.0              │ causeway_db_sqlmodel        │
└──────────────────┴───────────────────┴──────────────────────┘
```

The same view is available at `http://localhost:8000/__causeway` while `causeway dev` is running.

`/readyz` returns the aggregate: 200 once every plugin's `ready()` returns true; 503 with a per-plugin status JSON otherwise.

## Per-environment activation

```python
# src/app/plugins.py
from causeway import register, env

if env() == "prod":
    register(SentryObserver(dsn=settings.sentry_dsn.get_secret_value()))
    register(S3Storage(bucket=settings.s3_bucket))
else:
    register(LocalStorage(path="./tmp/uploads"))
```

The `env()` helper reads from the same `Settings` that drives the rest of the app — no special config plumbing.

## Plugin dependencies

A plugin can declare it depends on another contract being present. Startup ordering accounts for this automatically.

```python
class StripeBilling:
    contract_version = "v1.0"
    requires = ["DBSession", "KV"]   # Causeway starts these first
```

If a required contract has no registered adapter at startup, Causeway refuses to boot with a clear "plugin X requires Y, none registered" error.

## Authoring a plugin

1. Pick the contract(s) from `causeway.contracts`.
2. Implement them.
3. Expose a `plugin(settings)` entry point that registers your adapter.
4. Declare the contract version you target.

```python
# causeway-mailer-resend/__init__.py
from causeway import register
from causeway.contracts import Mailer
from resend import Resend  # hypothetical SDK

class ResendMailer(Mailer):
    contract_version = "v1.0"

    def __init__(self, api_key: str):
        self.client = Resend(api_key)

    async def startup(self, settings) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return True

    async def send(self, to: str, subject: str, body: str) -> None:
        await self.client.send(to=to, subject=subject, html=body)

def plugin(settings):
    register(ResendMailer(api_key=settings.resend_api_key.get_secret_value()))
```

```toml
# pyproject.toml
[project.entry-points."causeway.plugins"]
mailer-resend = "causeway_mailer_resend:plugin"

[project]
dependencies = ["causeway>=0.1,<2.0"]
```

The Causeway-side scaffolding for new plugins is automated:

```bash
$ causeway plugin new causeway-mailer-resend
```

This generates the package layout, the entry-point wiring, a `TestApp`-based smoke test, and a CI workflow.

## Naming convention

Official plugins use the `causeway-<role>-<impl>` prefix. The current shipping set:

- **tasks**: `causeway-tasks-dramatiq`
- **storage**: `causeway-storage-fs`, `causeway-storage-s3`
- **cache**: `causeway-cache-redis`
- **auth**: `causeway-auth-jwt`
- **mailer**: `causeway-mailer-smtp`
- **observe**: `causeway-observe-sentry`
- **flags**: `causeway-flags-growthbook`
- **db**: `causeway-db-sqlmodel`
- **deploy**: `causeway-deploy-docker`, `causeway-deploy-fly`, `causeway-deploy-modal`

Planned additions (and the full ecosystem inventory) are tracked in [`ROADMAP.md`](../ROADMAP.md#plugin-ecosystem). Third-party plugins should use `causeway-contrib-<thing>` to avoid implying official status.

## Contract stability

The plugin contract is part of the stable surface. After 1.0:

- Adding optional methods to a contract is non-breaking.
- Adding a new contract is non-breaking.
- Removing or renaming a contract method is **breaking** and follows the deprecation cycle in [`semver.md`](./stability/semver.md) — one full minor of `DeprecationWarning` before removal.

A plugin that targets Causeway `1.x` keeps working through every `1.y` release. Major bumps to Causeway require, at most, a corresponding major bump in the plugin — never a silent break.
