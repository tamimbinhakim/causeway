# Plugins

Quay is plugins-not-batteries by design. Core ships **contracts** and **one reference adapter** each. Picking a real implementation is a one-line install.

## What a plugin is

A plugin implements one or more of Quay's contracts:

| Contract       | What it does                                              | Reference impl               |
| -------------- | --------------------------------------------------------- | ---------------------------- |
| `TaskAdapter`  | Background jobs: enqueue, schedule, cron, eager test mode | `quay.tasks.InMemoryAdapter` |
| `Storage`      | Object storage: put / get / delete / signed URLs          | `quay.storage.LocalStorage`  |
| `KV`           | Key-value cache                                           | `quay.kv.MemoryKV`           |
| `AuthProvider` | `current_user(req)` resolution                            | none — bring your own        |

Reference adapters live in core. Production adapters live in sibling repos (e.g. `quay-storage-s3`).

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

Install it and it works. No explicit wiring needed.

### Explicit `register()` (when you need args)

```python
# src/app/plugins.py
from quay import register
from quay.tasks.dramatiq import DramatiqAdapter
from quay_storage_s3 import S3Storage
from app.config import settings

register(DramatiqAdapter(broker_url=settings.redis_url.get_secret_value()))
register(S3Storage(bucket="uploads"))
```

`plugins.py` runs once at startup, after `config.py` is loaded.

## Authoring a plugin

1. Pick a contract from `quay.contracts`.
2. Implement it.
3. Expose a `plugin(settings)` entry point that calls `register(YourAdapter(...))`.

```python
# quay-mailer-resend/__init__.py
from quay import register
from quay.contracts import Mailer
from resend import Resend  # hypothetical SDK

class ResendMailer(Mailer):
    def __init__(self, api_key: str):
        self.client = Resend(api_key)

    async def send(self, to: str, subject: str, body: str) -> None:
        await self.client.send(to=to, subject=subject, html=body)

def plugin(settings):
    register(ResendMailer(api_key=settings.resend_api_key.get_secret_value()))
```

```toml
# pyproject.toml
[project.entry-points."quay.plugins"]
mailer-resend = "quay_mailer_resend:plugin"
```

## Naming convention

Official plugins use the `quay-` prefix:

- `quay-sqlmodel` — SQLAlchemy / SQLModel session injection + Alembic glue
- `quay-auth-sessions`, `quay-auth-jwt`, `quay-auth-clerk`, `quay-auth-workos`
- `quay-storage-s3`
- `quay-mailer-resend`, `quay-mailer-postmark`
- `quay-deploy-modal`, `quay-deploy-fly`, `quay-deploy-lambda`

Third-party plugins should use `quay-contrib-<thing>` to avoid implying official status.

## Contract stability

The plugin contract is part of the stable surface. After 1.0:

- Adding optional methods to a contract is non-breaking.
- Adding a new contract is non-breaking.
- Removing or renaming a contract method is **breaking** and follows the standard deprecation cycle (see [`semver.md`](./semver.md)).

A plugin that targets Quay `1.x` keeps working through every `1.y` release. Major bumps to Quay require, at most, a corresponding major bump in the plugin.

## Listing what's installed

```
$ quay plugins
TaskAdapter   quay.tasks.dramatiq:DramatiqAdapter  (v0.2.1)
Storage       quay_storage_s3:S3Storage            (v0.3.0)
```

Same info appears at `http://localhost:8000/__quay` when running `quay dev`.
