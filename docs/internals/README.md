# Internals

A contributor's tour. These docs are aimed at people who are reading or modifying Quay itself — fixing a routing bug, writing a new plugin contract, cutting a release.

If you're trying to **use** Quay to build an app, you're in the wrong directory. Start at [the docs root](../README.md).

## In this directory

- **[Architecture](./architecture.md)** — the 30-second mental model and the layer-by-layer tour. What happens when you type `quay dev`.
- **[Code map](./code-map.md)** — every file in `packages/quay/src/quay/` annotated. The thing you read once and bookmark.
- **[Contributing (deep)](./contributing.md)** — beyond the top-level [CONTRIBUTING.md](../../CONTRIBUTING.md): coding conventions, when to add a comment vs. delete one, how to handle plugin packages, why a public symbol gets re-exported.
- **[Testing strategy](./testing.md)** — what we test, what we don't, where the bar is.
- **[Releases](./releases.md)** — how release-please drives PyPI publishes, what changes versioning, how to ship a hotfix.
- **[Writing a new official plugin](./plugin-authoring.md)** — the on-ramp for a maintainer adding a sibling `quay-<role>-<impl>` package.

## Quick orientation

```
quay/                                     # monorepo root (pnpm workspace)
├── packages/
│   ├── quay/                             # the core framework (PyPI: quay)
│   │   ├── src/quay/                     # see code-map.md
│   │   ├── tests/                        # pytest, asyncio mode auto
│   │   ├── pyproject.toml                # hatchling build, ruff/mypy/pytest config
│   │   └── pyrightconfig.json            # package-local pyright config
│   ├── quay-tasks-dramatiq/              # Dramatiq TaskAdapter
│   ├── quay-storage-s3/                  # S3 / R2 / MinIO Storage
│   ├── quay-storage-fs/                  # local filesystem Storage
│   ├── quay-cache-redis/                 # Redis KV / Cache
│   ├── quay-sqlmodel/                    # SQLModel DBSession
│   ├── quay-auth-jwt/                    # stateless JWT AuthProvider
│   ├── quay-mailer-smtp/                 # SMTP Mailer
│   ├── quay-flags-growthbook/            # FeatureFlags via GrowthBook
│   ├── quay-observe-sentry/              # Sentry observer plugin
│   ├── quay-deploy-docker/               # Dockerfile / Compose deploy target
│   ├── quay-deploy-fly/                  # Fly.io deploy target
│   └── quay-deploy-modal/                # Modal deploy target
├── examples/                             # runnable starter projects, not published
├── docs/                                 # what you're reading
├── pyrightconfig.json                    # root pyright config — points venv at packages/quay/.venv
└── .github/                              # CI, issue templates, workflows
```

## Where things live, at a glance

| Concern                      | Lives in                                    |
| ---------------------------- | ------------------------------------------- |
| File-based router            | `packages/quay/src/quay/routing.py`         |
| URL pattern translation      | `packages/quay/src/quay/_paths.py`          |
| Handler decorators           | `packages/quay/src/quay/_methods.py`        |
| App factory                  | `packages/quay/src/quay/app.py`             |
| Config (`Settings`)          | `packages/quay/src/quay/config.py`          |
| Scoped DI                    | `packages/quay/src/quay/scope.py`           |
| Plugin registry              | `packages/quay/src/quay/plugins.py`         |
| Plugin contracts (Protocols) | `packages/quay/src/quay/contracts.py`       |
| Reference adapters in core   | `packages/quay/src/quay/adapters.py`        |
| Background tasks             | `packages/quay/src/quay/tasks.py`           |
| Cron parser                  | `packages/quay/src/quay/_cron.py`           |
| Middleware base + `@guard`   | `packages/quay/src/quay/middleware.py`      |
| Observability (request id, OTel) | `packages/quay/src/quay/observability.py` |
| Errors + handlers            | `packages/quay/src/quay/errors.py`          |
| Health endpoints             | `packages/quay/src/quay/health.py`          |
| Diagnostics (`/__quay`)      | `packages/quay/src/quay/diagnostics.py`     |
| Testing kit                  | `packages/quay/src/quay/testing.py`         |
| CLI                          | `packages/quay/src/quay/cli.py`             |
| Scaffolding (`quay new`)     | `packages/quay/src/quay/_scaffold.py`       |

## The rule that decides most arguments

> If there are two reasonable ways to do something, one of them is wrong and we kill it.

That's it. That's the rule. It's why the docs are short and the code is short.
