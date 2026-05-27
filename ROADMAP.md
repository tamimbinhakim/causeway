# Roadmap

This is what's shipping when. Priorities shift, the world is
unpredictable. But it's the most honest plan I have.

If you want to influence it, the highest-leverage move is to open an
issue saying "I tried to use Causeway for X and it didn't work because Y."
That's worth more than ten feature requests.

## v0.1 — The MVP (12-week target)

The bet: get project shape and the developer loop right. Everything
else either rides on top or doesn't belong inside.

### Core (in `causeway`)

- [ ] **File-based router** — `$id.py`, `(group)/`, `_middleware.py`,
      `_scope.py`. Discovery via `pathlib.Path.glob()` +
      `importlib.util.spec_from_file_location()`. Emits route
      registrations into the IR.
- [ ] **Typed config** — `Settings` wraps `pydantic-settings`. Single
      `config.py` convention, hot-reload-aware re-validation in dev,
      `causeway.toml` `[client] expose_settings = [...]` exposes non-secret
      fields to the generated TS client.
- [ ] **DI container** — lifespan-scoped + request-scoped providers via
      `_scope.py`. `Annotated[T, provider]` slots. No `Provide()`
      wrapper objects, no global registry mutation.
- [ ] **Middleware / scope composition** — root → leaf order, response
      unwinds in reverse.
- [ ] **Plugin registry** — Python entry points (`causeway.plugins` group) + explicit `register()`. Manifest in `causeway.toml`. Per-contract
      registry, ordered registration, dependency declaration between
      plugins, per-environment activation, plugin-level health probes
      surfaced into `/readyz`.
- [ ] **Background task contract** — `@task` decorator, `enqueue()`,
      cron via `@cron(...)`. Dramatiq reference adapter shipped
      separately; in-process adapter ships with core for tests.
      `tasks_eager()` test mode.
- [ ] **Observability** — `structlog` defaults, request-id middleware,
      OTel auto-instrumentation hooks (no bundled exporter).
- [ ] **Health / readiness** — `/healthz` (liveness) + `/readyz`
      (every registered plugin's `ready()` returns true) built in.
- [ ] **Error overlay** — rich error page in dev; `application/problem+json`
      in prod.
- [ ] **CLI** — `causeway new`, `causeway dev`, `causeway build`, `causeway plugins`,
      `causeway deploy <target>`.
- [ ] **Testing kit** — `TestApp`, DI override surface, factory helpers.

### Examples

- [ ] `examples/minimal` — single `index.py` handler, no plugins.

## v0.2 — Hardening + stable surface

Everything we'd want true before tagging 1.0. The shape is mostly there;
v0.2 is about removing rough edges.

- [ ] **Route-tree diff in CI.** `causeway diff <old> <new>` flags removed
      routes / renamed fields / narrowed types as breaking.
- [ ] **WebSocket route convention** — `$id.ws.py`.
- [ ] **Coverage gate** — ≥ 85% across `causeway/*` source (CI-enforced).
- [ ] **Reproducible benchmark suite** — Causeway vs FastAPI vs Litestar
      across cold-start + p50/p95/p99 + req/s. The RPC substrate
      (`causeway._runtime`) doubles as the floor measurement.
- [ ] **Plugin sandbox tests** — fixtures that boot a causeway app with
      arbitrary plugin combos and run a smoke route to catch contract
      regressions.

## v0.3+ — Further out

Real, but unsized. Each lands when it earns its keep:

- [ ] Multi-tenancy `tenant` scope on `_scope.py`.
- [ ] Optional declarative resources à la Encore (`Database("primary")`,
      `Bucket("uploads")`) emitting Terraform/Pulumi stubs — opt-in,
      never required.

## v1.0 — Stability commitment

When we tag 1.0:

- [ ] **Plugin contracts frozen.** Backwards-compatible additions only.
- [ ] **Public API frozen for one minor release before breaking.**
      Removals and signature changes go through a deprecation cycle —
      see [`docs/semver.md`](docs/semver.md).
- [ ] **Documented LTS line.** Support windows + backport policy in
      [`docs/lts.md`](docs/lts.md).

Until 1.0: pre-release. Pin exact versions.

---

## Plugin ecosystem

The plugin contracts are the load-bearing surface for everything Causeway
deliberately doesn't ship. Reference adapters live in core (in-memory,
local-filesystem, in-process); production adapters are sibling packages.

What follows is the planned ecosystem. **No timeline** — each plugin
lands when there's enough demand to justify it and a real implementation
to validate against. Pull requests welcome; "I want X" without code
counts as a vote, not a commitment.

### Database / ORM

- `causeway-db-sqlmodel` — SQLAlchemy / SQLModel session provider + Alembic glue.
- `causeway-tortoise` — Tortoise ORM session + Aerich migrations.
- `causeway-piccolo` — Piccolo ORM provider + migrations.
- `causeway-prisma` — Prisma Python client provider.
- `causeway-sqlite` — single-file SQLite + WAL provider, zero deps.

### Auth

- `causeway-auth-sessions` — server-side session cookies + CSRF.
- `causeway-auth-jwt` — bearer JWT, key-rotation aware.
- `causeway-auth-clerk`
- `causeway-auth-workos`
- `causeway-auth-auth0`
- `causeway-auth-supabase`
- `causeway-auth-keycloak`
- `causeway-auth-firebase`

### Storage (blob / object)

- `causeway-storage-s3`
- `causeway-storage-r2`
- `causeway-storage-gcs`
- `causeway-storage-azure`
- `causeway-storage-minio`
- `causeway-storage-local` — fsspec-backed local FS (shipped with core for tests).

### Cache / KV

- `causeway-cache-redis`
- `causeway-cache-dragonfly`
- `causeway-cache-upstash`
- `causeway-cache-memcached`
- `causeway-cache-memory` — in-process LRU (shipped with core for tests).

### Sessions

- `causeway-sessions-cookie` — signed-cookie session.
- `causeway-sessions-redis` — server-side, Redis-backed.

### Task adapters (alternates to the Dramatiq reference)

- `causeway-tasks-celery`
- `causeway-tasks-arq`
- `causeway-tasks-taskiq`
- `causeway-tasks-rq`
- `causeway-tasks-huey`

### Long-running / workflows

- `causeway-jobs-temporal` — Temporal client + activity registration.
- `causeway-jobs-prefect`

### Mailer

- `causeway-mailer-resend`
- `causeway-mailer-postmark`
- `causeway-mailer-ses`
- `causeway-mailer-sendgrid`
- `causeway-mailer-mailgun`
- `causeway-mailer-smtp`

### Search

- `causeway-search-meilisearch`
- `causeway-search-typesense`
- `causeway-search-elastic`
- `causeway-search-algolia`

### PubSub / streaming

- `causeway-pubsub-redis`
- `causeway-pubsub-nats`
- `causeway-broker-kafka`

### Observability — tracing + logging

- `causeway-observe-sentry`
- `causeway-observe-signoz`
- `causeway-observe-honeycomb`
- `causeway-observe-datadog`
- `causeway-observe-tempo`

### Metrics

- `causeway-metrics-prometheus`
- `causeway-metrics-statsd`
- `causeway-metrics-otel` — OTLP metrics push.

### Rate limiting

- `causeway-ratelimit-redis`
- `causeway-ratelimit-memory` — in-process (tests, single-instance).

### Feature flags

- `causeway-flags-growthbook`
- `causeway-flags-flagsmith`
- `causeway-flags-unleash`
- `causeway-flags-launchdarkly`

### Payments

- `causeway-pay-stripe`
- `causeway-pay-paddle`
- `causeway-pay-lemonsqueezy`

### Security middleware

- `causeway-security-cors`
- `causeway-security-csrf`
- `causeway-security-headers` — HSTS, CSP, frame options, referrer policy.
- `causeway-security-trusted-hosts`

### Webhooks

- `causeway-webhooks` — signed inbound verification + retried, idempotent
  outbound dispatcher with a dead-letter queue.

### Schema export / interop

- `causeway-schema-openapi` — emit OpenAPI 3.1 off the route registrations.
- `causeway-schema-asyncapi` — emit AsyncAPI for streaming routes + pubsub.

### Deploy adapters

- `causeway-deploy-modal`
- `causeway-deploy-fly`
- `causeway-deploy-lambda` — via Mangum.
- `causeway-deploy-render`
- `causeway-deploy-railway`
- `causeway-deploy-aws-ecs`
- `causeway-deploy-gcp-run`
- `causeway-deploy-docker` — emits a working `Dockerfile` + `compose.yaml`.

### Plugin ergonomics (these help the ecosystem itself)

- `causeway-plugin-cookiecutter` — `causeway plugin new <name>` scaffolds a new
  plugin package wired to the right entry point, with CI, README, and a
  smoke test against a `TestApp`.
- `causeway-plugin-doctor` — `causeway plugin doctor` validates an installed
  plugin against the contract version it claims to implement.

---

## Maintenance commitments (every release)

- **Security.** CVEs in dependencies tracked weekly via Dependabot;
  patches land in a same-day point release.
- **Test gate.** Every PR runs ruff + mypy + pytest on macOS + Linux +
  Windows. No regressions land.
- **Examples kept runnable.** CI starts each example's server and runs a
  smoke `curl` against the typed routes.
- **Plugin contracts.** Any plugin authored against `causeway 1.x` keeps
  working through every `1.y`. Contract evolution follows the
  deprecation cycle in [`docs/semver.md`](docs/semver.md).

## Explicit non-goals (poster on the wall)

These are the lines I'm holding. If enough people push back I'll
reconsider — but the default is no.

1. **No ORM in core.** Ever.
2. **No admin panel in core.** Ever.
3. **No HTML rendering / template engine in core.** Ever.
4. **No infrastructure provisioning.** That's Terraform / Pulumi / Modal's
   job, not a framework's.
5. **No frontend.** Causeway emits a typed TypeScript client; what you do
   with it is your concern.

## Influences

In rough order of "how much I stole from each":

- **NestJS** — for modules, scoped providers, plugin lifecycle.
- **Litestar** — for "msgspec-first ASGI is viable" and clean DI scopes.
- **Encore.ts** — for proving declarative, type-driven backends work.
- **FastAPI** — for `Depends()` DI and dev-loop ergonomics.
- **`dyadpy`** — the lower-level typed-RPC primitive Causeway depends on
  for IR + TypeScript codegen + streaming.
- **AdonisJS / Laravel** — for what _not_ to do at the framework layer
  (the "ship every battery" model).

If you've worked on one of these and have opinions about what we should
steal next, please open an issue.
