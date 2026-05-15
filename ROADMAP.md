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
      `_layout.py`. Discovery via `pathlib.Path.glob()` +
      `importlib.util.spec_from_file_location()`. Emits route
      registrations into the Dyadpy IR.
- [ ] **Typed config** — `Settings` wraps `pydantic-settings`. Single
      `config.py` convention, hot-reload-aware re-validation in dev,
      `quay.toml` `[client] expose_settings = [...]` exposes non-secret
      fields to the generated TS client.
- [ ] **DI container** — lifespan-scoped + request-scoped providers via
      `_layout.py`. `Annotated[T, provider]` slots. No `Provide()`
      wrapper objects, no global registry mutation.
- [ ] **Middleware / layout composition** — root → leaf order, response
      unwinds in reverse. Matches Next.js / SvelteKit semantics 1:1.
- [ ] **Plugin registry** — Python entry points (`quay.plugins` group) + explicit `register()`. Manifest in `quay.toml`.
- [ ] **Background task contract** — `@task` decorator, `enqueue()`,
      cron via `@cron(...)`. Dramatiq reference adapter shipped
      separately; in-process adapter ships with core for tests.
      `tasks_eager()` test mode.
- [ ] **Observability** — `structlog` defaults, request-id middleware,
      OTel auto-instrumentation hooks (no bundled exporter).
- [ ] **Health / readiness** — `/healthz`, `/readyz` built in.
- [ ] **Error overlay** — rich error page in dev; `application/problem+json`
      in prod.
- [ ] **CLI** — `quay new`, `quay dev`, `quay build`, `quay deploy <target>`.
- [ ] **Testing kit** — `TestApp`, DI override surface, factory helpers.

### Out of core, ships as official plugins (own repos)

- [ ] `quay-sqlmodel` — SQLAlchemy/SQLModel session injection + Alembic glue.
- [ ] `quay-auth-sessions`, `quay-auth-jwt`, `quay-auth-clerk`, `quay-auth-workos`.
- [ ] `quay-storage-s3` (fsspec-backed local also).
- [ ] `quay-mailer-resend`, `quay-mailer-postmark`.
- [ ] `quay-deploy-modal`, `quay-deploy-fly`, `quay-deploy-lambda`.

### Examples

- [ ] `examples/minimal` — single `index.py` handler, no plugins.

## v0.2 — Hardening + stable surface

Everything we'd want true before tagging 1.0. The shape is mostly there;
v0.2 is about removing rough edges.

- [ ] **Route-tree diff in CI.** `quay diff <old> <new>` flags removed
      routes / renamed fields / narrowed types as breaking.
- [ ] **WebSocket route convention** — `[id].ws.py`.
- [ ] **Webhook plugin** — signed inbound + retried outbound.
- [ ] **Coverage gate** — ≥ 85% across `quay/*` source (CI-enforced).
- [ ] **Reproducible benchmark suite** — Quay vs raw Dyadpy vs FastAPI vs
      Litestar across cold-start + p50/p95/p99 + req/s.

## v0.3+ — Further out

Real, but unsized. Each lands when it earns its keep:

- [ ] Multi-tenancy `tenant` scope on `_layout.py`.
- [ ] Optional declarative resources à la Encore (`Database("primary")`,
      `Bucket("uploads")`) emitting Terraform/Pulumi stubs — opt-in,
      never required.

## v1.0 — Stability commitment

When we tag 1.0:

- [ ] **Plugin contract frozen.** Backwards-compatible additions only.
- [ ] **Public API frozen for one minor release before breaking.**
      Removals and signature changes go through a deprecation cycle —
      see [`docs/semver.md`](docs/semver.md).
- [ ] **Documented LTS line.** Support windows + backport policy in
      [`docs/lts.md`](docs/lts.md).

Until 1.0: pre-release. Pin exact versions.

## Maintenance commitments (every release)

- **Security.** CVEs in dependencies tracked weekly via Dependabot;
  patches land in a same-day point release.
- **Test gate.** Every PR runs ruff + mypy + pytest on macOS + Linux +
  Windows. No regressions land.
- **Examples kept runnable.** CI starts each example's server and runs a
  smoke `curl` against the typed routes.

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
6. **No frontend.** Dyadpy ships a TS client; what you do with it is your
   concern.

## Influences

In rough order of "how much I stole from each":

- **Next.js / SvelteKit** — for `[id]/`, `(group)/`, `_layout`, `_middleware`.
- **Encore.ts** — for proving declarative, type-driven backends work.
- **Litestar / NestJS** — for the "structural framework, not batteries"
  shape.
- **Dyadpy** — for the wire-level primitives Quay sits on.
- **AdonisJS / Laravel** — for what _not_ to do at the framework layer.

If you've worked on one of these and have opinions about what we should
steal next, please open an issue.
