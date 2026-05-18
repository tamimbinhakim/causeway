# Causeway docs

A lean backend framework for type-safe Python APIs. The folder tree is the route table; the typed TypeScript client falls out the other end for free.

If you're new here, [the story behind why this exists](./why-causeway.md) is the warmest place to start.

---

## Getting started

The smallest possible loop from install to a typed handler responding to `curl`.

- **[Installation](./getting-started/installation.md)** — `uv add causeway`, scaffold a new app.
- **[Project structure](./getting-started/project-structure.md)** — what `causeway new` creates and where things live.
- **[Your first route](./getting-started/first-route.md)** — write a handler, run it, see the generated TS client.

## Building your application

Per-concept guides for everything you do day-to-day.

### Routing

- **[Defining routes](./building/routing/defining-routes.md)** — file-based routing, folder style and dot-flat style.
- **[Dynamic segments](./building/routing/dynamic-segments.md)** — `[id]`, `$id`, type binding.
- **[Route groups](./building/routing/route-groups.md)** — `(admin)/` for organization without changing URLs.
- **[Middleware](./building/routing/middleware.md)** — per-subtree wrappers via `_middleware.py`.
- **[Scopes](./building/routing/scopes.md)** — request-scoped DI and lifespan hooks via `_scope.py`.

### Handlers

- **[HTTP methods](./building/handlers/methods.md)** — `@get`, `@post`, `@put`, `@patch`, `@delete`.
- **[Params and body](./building/handlers/params-and-body.md)** — path params, query, body, headers, deps.
- **[Responses](./building/handlers/responses.md)** — return types, status codes, custom headers.
- **[Errors](./building/handlers/errors.md)** — `HttpError`, `@raises`, problem+json.
- **[Streaming](./building/handlers/streaming.md)** — `stream[T]` for SSE.
- **[Pagination](./building/handlers/pagination.md)** — `Paginated[T]`, `Cursor`.
- **[Batch endpoints](./building/handlers/batch.md)** — `BatchResult[T, E]`, `@batch`, HTTP 207.
- **[Idempotency keys](./building/handlers/idempotency.md)** — replaying responses for retried requests.
- **[File uploads](./building/handlers/file-uploads.md)** — presigned PUTs to object storage.
- **[Permissions](./building/handlers/permissions.md)** — `require_permission` and the default model.
- **[Multi-tenant apps](./building/multi-tenant.md)** — workspace-scoped routes via `_scope.py`.

### Application primitives

- **[Configuration](./building/config/index.md)** — `Settings`, `causeway.toml`, secrets.
- **[Plugins](./building/plugins/index.md)** — install adapters, write your own.
- **[Background tasks](./building/tasks/index.md)** — `@task`, `@cron`, adapter swap.
- **[Events](./building/events/index.md)** — file-based listeners and `emit` for in-process fan-out.
- **[Testing](./building/testing/index.md)** — `TestApp`, inline scenarios, snapshots.
- **[Observability](./building/observability/index.md)** — request IDs, structured logs, OTel.
- **[Typed client](./building/typed-client/index.md)** — what's in `client.ts` and how to consume it.
- **[Webhooks (outgoing)](./building/webhooks/index.md)** — register endpoints, send events, retry behavior.
- **[Verifying incoming webhooks](./building/webhooks/incoming.md)** — HMAC + timestamp checks for inbound calls.

## API Reference

Per-symbol pages.

- **[Decorators](./api-reference/decorators/get.md)** — `@get`, `@post`, …, `@task`, `@cron`, `@provide`, `@guard`, `@raises`.
- **[Functions](./api-reference/functions/create-app.md)** — `create_app`, `register`, `env`, `configure_logging`, `configure_otel`, `emit`, `tasks_eager`, `discover`.
- **[Classes](./api-reference/classes/Middleware.md)** — `Middleware`, `Settings`, `Manifest`, `TestApp`, `RequestIdMiddleware`, `TaskRef`, `TaskState`, contracts, errors.
- **[CLI](./api-reference/cli/index.md)** — `causeway new`, `dev`, `build` (with `--binary`), `freeze`, `plugins`, `plugin new`, `diff`, `deploy`, `version`.
- **[File conventions](./api-reference/file-conventions/index.md)** — `index.py`, `[name].py`, `$name`, `(group)/`, `_middleware.py`, `_scope.py`, `causeway.toml`.

Full index: **[API Reference](./api-reference/index.md)**.

## Architecture

What happens under the hood.

- **[Boot pipeline](./architecture/boot-pipeline.md)** — what runs between `causeway dev` and your first request.
- **[IR flow](./architecture/ir-flow.md)** — how a handler signature becomes a typed TS client.
- **[Hot reload](./architecture/hot-reload.md)** — what's preserved across reloads, what isn't.

## Deploying

- **[Deploying overview](./deploying/index.md)** — health checks, env, the production checklist.
- **[Docker](./deploying/docker.md)** · **[Fly.io](./deploying/fly.md)** · **[Modal](./deploying/modal.md)** · **[Binary export](./deploying/binary.md)**

## Upgrading

- **[Upgrading overview](./upgrading/index.md)** — version status, deprecation policy.
- **[Alpha → 0.1.0](./upgrading/alpha-to-0-1-0.md)** — what to expect when the API freeze ships.

## Stability

- **[Versioning](./stability/semver.md)** — what counts as a breaking change.
- **[IR stability](./stability/ir-stability.md)** — what flows into the IR, how it evolves.
- **[LTS](./stability/lts.md)** — support windows, backport policy.

## Internals

For people working **on** Causeway rather than building **with** it.

- **[Architecture](./internals/architecture.md)** — high-level source layout.
- **[Code map](./internals/code-map.md)** — file-by-file tour of `packages/causeway/src/causeway/`.
- **[Contributing (deep)](./internals/contributing.md)** — coding conventions beyond the top-level CONTRIBUTING.md.
- **[Testing strategy](./internals/testing.md)** — what we test, what we don't.
- **[Releases](./internals/releases.md)** — how release-please drives PyPI publishes.
- **[Writing a new official plugin](./internals/plugin-authoring.md)** — the on-ramp for sibling `causeway-<role>-<impl>` packages.

---

## Why Causeway

The long version of the story behind the framework: **[Why Causeway](./why-causeway.md)**.

---

Something wrong, confusing, or missing? Open a [doc issue](https://github.com/tamimbinhakim/causeway/issues/new?labels=docs). Meta-PRs (improving these very docs) count and are appreciated.
