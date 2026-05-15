# Roadmap

This is what's shipping when. Priorities shift, the world is
unpredictable. But it's the most honest plan I have.

If you want to influence it, the highest-leverage move is to open an
issue saying "I tried to use Quay for X and it didn't work because Y."
That's worth more than ten feature requests.

## v0.1 — The MVP (12-week target)

The bet: get project shape and the developer loop right. Everything
else either rides on top or doesn't belong inside.

### Core (in `quay`)

- [ ] **File-based router** — `[id].py`, `(group)/`, `_middleware.py`,
      `_scope.py`. Discovery via `pathlib.Path.glob()` +
      `importlib.util.spec_from_file_location()`. Emits route
      registrations into the IR.
- [ ] **Typed config** — `Settings` wraps `pydantic-settings`. Single
      `config.py` convention, hot-reload-aware re-validation in dev,
      `quay.toml` `[client] expose_settings = [...]` exposes non-secret
      fields to the generated TS client.
- [ ] **DI container** — lifespan-scoped + request-scoped providers via
      `_scope.py`. `Annotated[T, provider]` slots. No `Provide()`
      wrapper objects, no global registry mutation.
- [ ] **Middleware / scope composition** — root → leaf order, response
      unwinds in reverse.
- [ ] **Plugin registry** — Python entry points (`quay.plugins` group) + explicit `register()`. Manifest in `quay.toml`. Per-contract
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
- [ ] **CLI** — `quay new`, `quay dev`, `quay build`, `quay plugins`,
      `quay deploy <target>`.
- [ ] **Testing kit** — `TestApp`, DI override surface, factory helpers.

### Examples

- [ ] `examples/minimal` — single `index.py` handler, no plugins.

## v0.2 — Hardening + stable surface

Everything we'd want true before tagging 1.0. The shape is mostly there;
v0.2 is about removing rough edges.

- [ ] **Route-tree diff in CI.** `quay diff <old> <new>` flags removed
      routes / renamed fields / narrowed types as breaking.
- [ ] **WebSocket route convention** — `[id].ws.py`.
- [ ] **Coverage gate** — ≥ 85% across `quay/*` source (CI-enforced).
- [ ] **Reproducible benchmark suite** — Quay vs FastAPI vs Litestar vs
      the underlying RPC layer (raw `dyadpy`) across cold-start +
      p50/p95/p99 + req/s.
- [ ] **Plugin sandbox tests** — fixtures that boot a quay app with
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

The plugin contracts are the load-bearing surface for everything Quay
deliberately doesn't ship. Reference adapters live in core (in-memory,
local-filesystem, in-process); production adapters are sibling packages.

What follows is the planned ecosystem. **No timeline** — each plugin
lands when there's enough demand to justify it and a real implementation
to validate against. Pull requests welcome; "I want X" without code
counts as a vote, not a commitment.

### Database / ORM

- `quay-sqlmodel` — SQLAlchemy / SQLModel session provider + Alembic glue.
- `quay-tortoise` — Tortoise ORM session + Aerich migrations.
- `quay-piccolo` — Piccolo ORM provider + migrations.
- `quay-prisma` — Prisma Python client provider.
- `quay-sqlite` — single-file SQLite + WAL provider, zero deps.

### Auth

- `quay-auth-sessions` — server-side session cookies + CSRF.
- `quay-auth-jwt` — bearer JWT, key-rotation aware.
- `quay-auth-clerk`
- `quay-auth-workos`
- `quay-auth-auth0`
- `quay-auth-supabase`
- `quay-auth-keycloak`
- `quay-auth-firebase`

### Storage (blob / object)

- `quay-storage-s3`
- `quay-storage-r2`
- `quay-storage-gcs`
- `quay-storage-azure`
- `quay-storage-minio`
- `quay-storage-local` — fsspec-backed local FS (shipped with core for tests).

### Cache / KV

- `quay-cache-redis`
- `quay-cache-dragonfly`
- `quay-cache-upstash`
- `quay-cache-memcached`
- `quay-cache-memory` — in-process LRU (shipped with core for tests).

### Sessions

- `quay-sessions-cookie` — signed-cookie session.
- `quay-sessions-redis` — server-side, Redis-backed.

### Task adapters (alternates to the Dramatiq reference)

- `quay-tasks-celery`
- `quay-tasks-arq`
- `quay-tasks-taskiq`
- `quay-tasks-rq`
- `quay-tasks-huey`

### Long-running / workflows

- `quay-jobs-temporal` — Temporal client + activity registration.
- `quay-jobs-prefect`

### Mailer

- `quay-mailer-resend`
- `quay-mailer-postmark`
- `quay-mailer-ses`
- `quay-mailer-sendgrid`
- `quay-mailer-mailgun`
- `quay-mailer-smtp`

### Search

- `quay-search-meilisearch`
- `quay-search-typesense`
- `quay-search-elastic`
- `quay-search-algolia`

### PubSub / streaming

- `quay-pubsub-redis`
- `quay-pubsub-nats`
- `quay-broker-kafka`

### Observability — tracing + logging

- `quay-observe-sentry`
- `quay-observe-signoz`
- `quay-observe-honeycomb`
- `quay-observe-datadog`
- `quay-observe-tempo`

### Metrics

- `quay-metrics-prometheus`
- `quay-metrics-statsd`
- `quay-metrics-otel` — OTLP metrics push.

### Rate limiting

- `quay-ratelimit-redis`
- `quay-ratelimit-memory` — in-process (tests, single-instance).

### Feature flags

- `quay-flags-growthbook`
- `quay-flags-flagsmith`
- `quay-flags-unleash`
- `quay-flags-launchdarkly`

### Payments

- `quay-pay-stripe`
- `quay-pay-paddle`
- `quay-pay-lemonsqueezy`

### Security middleware

- `quay-security-cors`
- `quay-security-csrf`
- `quay-security-headers` — HSTS, CSP, frame options, referrer policy.
- `quay-security-trusted-hosts`

### Webhooks

- `quay-webhooks` — signed inbound verification + retried, idempotent
  outbound dispatcher with a dead-letter queue.

### Schema export / interop

- `quay-schema-openapi` — emit OpenAPI 3.1 off the route registrations.
- `quay-schema-asyncapi` — emit AsyncAPI for streaming routes + pubsub.

### Deploy adapters

- `quay-deploy-modal`
- `quay-deploy-fly`
- `quay-deploy-lambda` — via Mangum.
- `quay-deploy-render`
- `quay-deploy-railway`
- `quay-deploy-aws-ecs`
- `quay-deploy-gcp-run`
- `quay-deploy-docker` — emits a working `Dockerfile` + `compose.yaml`.

### Plugin ergonomics (these help the ecosystem itself)

- `quay-plugin-cookiecutter` — `quay plugin new <name>` scaffolds a new
  plugin package wired to the right entry point, with CI, README, and a
  smoke test against a `TestApp`.
- `quay-plugin-doctor` — `quay plugin doctor` validates an installed
  plugin against the contract version it claims to implement.

---

## Maintenance commitments (every release)

- **Security.** CVEs in dependencies tracked weekly via Dependabot;
  patches land in a same-day point release.
- **Test gate.** Every PR runs ruff + mypy + pytest on macOS + Linux +
  Windows. No regressions land.
- **Examples kept runnable.** CI starts each example's server and runs a
  smoke `curl` against the typed routes.
- **Plugin contracts.** Any plugin authored against `quay 1.x` keeps
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
5. **No AI / LLM types in core.** No `quay.ai` module, no `Thread` / `@agent`
   / `VectorStore` primitives, no LLM-shaped helpers. Those are user code
   or a separate library (LangGraph / Pydantic AI / Mastra). Quay binds
   the web/task surface; what flows through it is your problem.
6. **No frontend.** Quay emits a typed TypeScript client; what you do
   with it is your concern.

## Influences

In rough order of "how much I stole from each":

- **NestJS** — for modules, scoped providers, plugin lifecycle.
- **Litestar** — for "msgspec-first ASGI is viable" and clean DI scopes.
- **Encore.ts** — for proving declarative, type-driven backends work.
- **FastAPI** — for `Depends()` DI and dev-loop ergonomics.
- **`dyadpy`** — the lower-level typed-RPC primitive Quay depends on
  for IR + TypeScript codegen + streaming.
- **AdonisJS / Laravel** — for what _not_ to do at the framework layer
  (the "ship every battery" model).

If you've worked on one of these and have opinions about what we should
steal next, please open an issue.
