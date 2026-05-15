# Plugins

Quay is plugins-not-batteries by design. The plugin system **is** the framework's surface for everything Quay deliberately doesn't ship: ORMs, auth, storage, mail, caches, search, rate limiting, payments, observability, deploy targets — all of it.

This page describes the contracts, the lifecycle, the registry, and how to author one.

## The shape of a plugin

A plugin is a Python package that:

1. **Implements one or more contracts.** Contracts are `typing.Protocol`s declared in `quay.contracts`. A single package may implement several (e.g. a plugin that provides both `Storage` and `Mailer`).
2. **Exposes a `plugin(settings)` callable** as the `quay.plugins` entry point. Quay calls this once at startup with the validated `Settings` object, and the callable registers its adapters via `quay.register(...)`.
3. **Declares its supported Quay contract versions** in `pyproject.toml` so the registry can warn when a plugin targets an older protocol.

That's the entire surface a plugin author has to learn.

## Built-in contracts

Each contract ships with a reference adapter in core (or in a sibling repo for plugins that need a real dependency). Picking a real backend is a one-line swap in `plugins.py`.

| Contract       | Method surface (sketch)                                               | Reference impl                    |
| -------------- | --------------------------------------------------------------------- | --------------------------------- |
| `TaskAdapter`  | `enqueue`, `schedule`, `cron`, `eager` (test ctx), `status`, `result` | `quay.tasks.InMemoryAdapter`      |
| `Storage`      | `put`, `get`, `delete`, `signed_url`, `list`                          | `quay.storage.LocalStorage`       |
| `KV`           | `get`, `set` (with TTL), `delete`, `incr`, `expire`                   | `quay.kv.MemoryKV`                |
| `SessionStore` | `read`, `write`, `destroy`, `rotate`                                  | `quay.sessions.CookieStore`       |
| `Mailer`       | `send(to, subject, body, ...)`, `send_template`, `verify_address`     | none — bring your own             |
| `Searchable`   | `index`, `search`, `delete`, `bulk_index`                             | none — bring your own             |
| `RateLimiter`  | `acquire(key, cost=1)`, `peek`, `reset`                               | `quay.ratelimit.MemoryLimiter`    |
| `FeatureFlags` | `is_on(flag, user=None)`, `variant`, `refresh`                        | `quay.flags.StaticFlags`          |
| `MetricsSink`  | `counter`, `gauge`, `histogram`, `timer`                              | `quay.metrics.NullSink`           |
| `LogSink`      | `emit(record)` — receives structured log records for forwarding       | stdout via `structlog`            |
| `PubSub`       | `publish(topic, payload)`, `subscribe(topic, handler)`                | `quay.pubsub.MemoryBus`           |
| `AuthProvider` | `current_user(req)`, `login(creds)`, `logout(req)`, `verify(token)`   | none — bring your own             |
| `DBSession`    | `session()` (request-scoped), `transaction()`, `health()`             | none — provided by ORM plugins    |
| `BlobScanner`  | `scan(stream)` for incoming-file virus / type checks                  | `quay.scanner.NullScanner`        |
| `DeployTarget` | `manifest()`, `package()`, `push(target)`                             | none — provided by deploy plugins |

Contracts are versioned. `quay.contracts.v1.Storage` is the stable surface; new optional methods land in minor releases (`v1.1`), breaking changes wait for `v2`. See [`semver.md`](./semver.md) for the rules.

## Two discovery paths

### Entry points (automatic)

Any installed package that declares a `quay.plugins` entry point is auto-loaded at startup:

```toml
# quay-storage-s3/pyproject.toml
[project.entry-points."quay.plugins"]
storage-s3 = "quay_storage_s3:plugin"
```

```python
# quay_storage_s3/__init__.py
from quay import register
from .store import S3Storage

def plugin(settings):
    register(S3Storage(bucket=settings.s3_bucket))
```

Install it (`uv add quay-storage-s3`) and it works. No explicit wiring needed.

### Explicit `register()` (when you need args or ordering)

```python
# src/app/plugins.py
from quay import register
from quay.tasks.dramatiq import DramatiqAdapter
from quay_storage_s3 import S3Storage
from quay_observe_sentry import SentryObserver
from app.config import settings

register(SentryObserver(dsn=settings.sentry_dsn.get_secret_value()))   # first — wraps everything else
register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
register(S3Storage(bucket="uploads"))
```

`plugins.py` runs once at startup, after `config.py` is loaded. Registration order is preserved; later registrations override earlier ones for the same contract slot.

## Lifecycle

A plugin goes through four phases:

1. **Discovered.** Entry-point scan picks it up, or `register()` is called.
2. **Validated.** Its declared contract version is checked against the loaded Quay version. Incompatible plugins fail fast with a clear error.
3. **Started.** Quay calls `plugin.startup(settings)` if defined. This is where DB pools open, brokers connect, etc.
4. **Ready.** Quay polls `plugin.ready()` until it returns `True`. `/readyz` returns 503 until every registered plugin is ready.

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
$ quay plugins
Contract        Adapter                                Version   Ready
TaskAdapter     quay.tasks.dramatiq:DramatiqAdapter    0.2.1     ✓
Storage         quay_storage_s3:S3Storage              0.3.0     ✓
KV              quay_cache_redis:RedisKV               0.1.4     ✓
Mailer          quay_mailer_resend:ResendMailer        0.1.0     ✓
DBSession       quay_sqlmodel:SQLModelSession          0.4.2     ✓
```

The same view is available at `http://localhost:8000/__quay` while `quay dev` is running.

`/readyz` returns the aggregate: 200 once every plugin's `ready()` returns true; 503 with a per-plugin status JSON otherwise.

## Per-environment activation

```python
# src/app/plugins.py
from quay import register, env

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
    requires = ["DBSession", "KV"]   # Quay starts these first
```

If a required contract has no registered adapter at startup, Quay refuses to boot with a clear "plugin X requires Y, none registered" error.

## Authoring a plugin

1. Pick the contract(s) from `quay.contracts`.
2. Implement them.
3. Expose a `plugin(settings)` entry point that registers your adapter.
4. Declare the contract version you target.

```python
# quay-mailer-resend/__init__.py
from quay import register
from quay.contracts import Mailer
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
[project.entry-points."quay.plugins"]
mailer-resend = "quay_mailer_resend:plugin"

[project]
dependencies = ["quay>=0.1,<2.0"]
```

The Quay-side scaffolding for new plugins is automated:

```bash
$ quay plugin new quay-mailer-resend
```

This generates the package layout, the entry-point wiring, a `TestApp`-based smoke test, and a CI workflow.

## Naming convention

Official plugins use the `quay-` prefix:

- `quay-sqlmodel` — SQLAlchemy / SQLModel session injection + Alembic glue
- `quay-auth-sessions`, `quay-auth-jwt`, `quay-auth-clerk`, `quay-auth-workos`, `quay-auth-auth0`, `quay-auth-supabase`
- `quay-storage-s3`, `quay-storage-r2`, `quay-storage-gcs`, `quay-storage-azure`, `quay-storage-minio`
- `quay-cache-redis`, `quay-cache-dragonfly`, `quay-cache-memcached`, `quay-cache-upstash`
- `quay-sessions-cookie`, `quay-sessions-redis`
- `quay-tasks-celery`, `quay-tasks-arq`, `quay-tasks-taskiq`, `quay-tasks-rq`, `quay-tasks-huey`
- `quay-mailer-resend`, `quay-mailer-postmark`, `quay-mailer-ses`, `quay-mailer-sendgrid`, `quay-mailer-mailgun`, `quay-mailer-smtp`
- `quay-search-meilisearch`, `quay-search-typesense`, `quay-search-elastic`, `quay-search-algolia`
- `quay-observe-sentry`, `quay-observe-signoz`, `quay-observe-honeycomb`, `quay-observe-datadog`
- `quay-metrics-prometheus`, `quay-metrics-statsd`, `quay-metrics-otel`
- `quay-ratelimit-redis`, `quay-ratelimit-memory`
- `quay-flags-growthbook`, `quay-flags-flagsmith`, `quay-flags-unleash`, `quay-flags-launchdarkly`
- `quay-pay-stripe`, `quay-pay-paddle`, `quay-pay-lemonsqueezy`
- `quay-security-cors`, `quay-security-csrf`, `quay-security-headers`, `quay-security-trusted-hosts`
- `quay-webhooks` — signed inbound + retried, idempotent outbound
- `quay-pubsub-redis`, `quay-pubsub-nats`, `quay-broker-kafka`
- `quay-jobs-temporal`, `quay-jobs-prefect`
- `quay-schema-openapi`, `quay-schema-asyncapi`
- `quay-deploy-modal`, `quay-deploy-fly`, `quay-deploy-lambda`, `quay-deploy-render`, `quay-deploy-railway`, `quay-deploy-aws-ecs`, `quay-deploy-gcp-run`, `quay-deploy-docker`

Full ecosystem inventory in [`ROADMAP.md`](../ROADMAP.md#plugin-ecosystem).

Third-party plugins should use `quay-contrib-<thing>` to avoid implying official status.

## Contract stability

The plugin contract is part of the stable surface. After 1.0:

- Adding optional methods to a contract is non-breaking.
- Adding a new contract is non-breaking.
- Removing or renaming a contract method is **breaking** and follows the deprecation cycle in [`semver.md`](./semver.md) — one full minor of `DeprecationWarning` before removal.

A plugin that targets Quay `1.x` keeps working through every `1.y` release. Major bumps to Quay require, at most, a corresponding major bump in the plugin — never a silent break.
