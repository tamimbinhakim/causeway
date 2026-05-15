# Writing a new official plugin

The on-ramp for adding a sibling `quay-<role>-<impl>` package to the monorepo. Aimed at maintainers, not external authors — external plugin authors should read [`docs/plugins.md`](../plugins.md).

## Decide on the name

Naming convention is `quay-<role>-<impl>`:

- `<role>` is the contract family (`tasks`, `storage`, `cache`, `auth`, `mailer`, `flags`, `observe`, `db`, `deploy`, …).
- `<impl>` is the concrete implementation (`dramatiq`, `s3`, `redis`, `jwt`, `smtp`, `growthbook`, `sentry`, `sqlmodel`, `fly`, …).

PyPI name uses hyphens: `quay-tasks-dramatiq`. Python import name uses underscores: `quay_tasks_dramatiq`. Class name uses CamelCase: `DramatiqAdapter`, `S3Storage`, `JwtAuth`, `SmtpMailer`.

If your role is new (no existing `quay-<role>-*` packages), open a Discussion first. Adding a contract family is a bigger decision than adding an implementation.

## Scaffold the package

```bash
quay plugin new quay-<role>-<impl>
```

That generates:

```
packages/quay-<role>-<impl>/
├── src/quay_<role>_<impl>/
│   └── __init__.py
├── tests/
│   └── test_smoke.py
├── pyproject.toml
└── README.md
```

The generated `pyproject.toml` declares the entry point:

```toml
[project.entry-points."quay.plugins"]
<role>-<impl> = "quay_<role>_<impl>:plugin"
```

## Implement the contract

Pick the protocol from `quay.contracts` and implement it. Minimum surface:

```python
# packages/quay-<role>-<impl>/src/quay_<role>_<impl>/__init__.py
from typing import Any, ClassVar
from quay.contracts import <Role>   # e.g. TaskAdapter, Storage, Mailer


class <Impl><Role>Adapter:
    """One sentence on what backend this wraps."""

    contract_version: ClassVar[str] = "v1.0"

    def __init__(self, *args, **kwargs) -> None: ...

    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return True

    # contract-specific methods …


def plugin(settings: Any) -> None:
    """Entry-point callable. Reads settings, calls register()."""
    from quay import register

    if settings is None:
        return   # discovery pass — Settings isn't loaded yet

    field = getattr(settings, "<your_setting>", None)
    if not field:
        return   # not configured for this app; skip silently

    register(<Impl><Role>Adapter(<field>=field))
```

Notes:

- `startup(settings)` runs after Settings is loaded — that's where you open connection pools, create clients, etc.
- `shutdown()` runs in reverse-of-registration order.
- `ready()` is polled by `/readyz`. Return `False` while the connection isn't established yet; return `True` once it is.
- Don't raise from `startup` for missing config. Skip silently and let `/readyz` reflect the unready state, **or** raise with a message that points at the missing setting.

## Add a `settings_fragment` (optional)

If your plugin needs settings fields the app didn't declare:

```python
class <Impl><Role>Adapter:
    def settings_fragment(self) -> dict[str, Any]:
        return {"<your_setting>": SecretStr(...)}
```

The registry merges these into `Settings` at startup. Use `SecretStr` / `SecretBytes` for anything secret — those fields are stripped from `/__quay` and the generated TS client automatically.

## Test the adapter

Minimum test coverage:

1. **Smoke test** — `adapter = <Adapter>(...); await adapter.startup(None); assert await adapter.ready()`.
2. **Contract round-trip** — implement the protocol's main verbs and assert against the in-memory reference where possible.
3. **`plugin(settings)` entry point** — pass a minimal Settings-like object and assert `register` was called.

If the adapter wraps a network service (Redis, S3, Postgres), use a stub or a `testcontainers` integration test. Don't require live credentials in CI.

## Wire CI

The package inherits the monorepo's CI workflow — `pnpm test` runs every package's pytest. You usually don't need to add a workflow file.

If your package needs extra dependencies for tests (e.g. `testcontainers`), add them under `[dependency-groups] dev` in the package's `pyproject.toml`.

## Document it

In the package's own `README.md`:

- One paragraph on what backend this wraps and why someone would pick it over alternatives.
- The settings fields it reads.
- A minimal `register(...)` example for the explicit-registration path.

If your adapter has noteworthy contract behavior (cron not supported, eager mode uses stub broker, ready check is best-effort, etc.), say so explicitly.

## Promote in the main docs

If the plugin is meant to be official:

1. Add it to the "Naming convention" / "shipping set" list in [`docs/plugins.md`](../plugins.md).
2. Add it to the package table in the root [`README.md`](../../README.md) when it's stable.
3. Update [`ROADMAP.md`](../../ROADMAP.md) — move the package from "planned" to "shipped".

If it's a third-party plugin (not part of the official set), the right place is the curated registry on the docs site (forthcoming) — not the in-repo lists.

## Ship it

The package follows the same release flow as core (see [`releases.md`](./releases.md)). Conventional Commits scope the bump, release-please opens the release PR, the publish workflow ships to PyPI.

The first release should be `0.1.0a0` (alpha). Stabilize at `0.1.0` once the API has settled.
