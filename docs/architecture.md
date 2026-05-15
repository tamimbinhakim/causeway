# Architecture

This is what's actually happening when you type `quay dev`. It's not magic,
and the parts are small enough that you can read the whole thing in a
weekend.

> **One-line acknowledgement.** Quay's typed-RPC layer — the IR format,
> the TypeScript codegen, the streaming envelope — is provided by `dyadpy`,
> a lower-level primitive that Quay depends on. Everything below
> describes Quay's surface; the IR / codegen plumbing under it is mostly
> Dyadpy doing its job. From an application author's perspective: it's
> all Quay.

## The 30-second mental model

```
src/app/routes/**/*.py
        │
        ▼
  File-Router         (pathlib.glob + importlib.spec_from_file_location)
        │
        ▼
   Route registrations  ──►  IR  ──►  ASGI runtime  ──►  HTTP / SSE
        │                    │
        ▼                    ▼
  _middleware.py          quay.toml manifest
  _scope.py                    │
        │                      ▼
        ▼                  Generated client.ts
   Scoped DI graph
```

Two flows: **server start** walks the `routes/` tree and registers
everything into the IR; **at request time** the ASGI runtime composes
middleware + scopes + handler from the precomputed graph.

## Layer by layer

### 1. File-based router (`quay.routing`)

The router walks `src/app/routes/**/*.py`, ignoring underscore-prefixed
files (those are private). For each file:

1. Translate the filename + path into a URL pattern. `[id].py` becomes
   `{id}`, `(group)/` is stripped, `index.py` is the folder URL.
2. Load the module via `importlib.util.spec_from_file_location()` — this
   is how brackets-in-filenames work without breaking Python's import
   system.
3. Find handler exports decorated with `@get` / `@post` / etc., and
   register them into the route table.

Two file conventions are special:

- `_middleware.py` — its `middleware = [...]` list wraps every route in
  the same subtree.
- `_scope.py` — its `provide(...)` registrations are available to every
  handler in the subtree, request-scoped, plus optional `startup()` /
  `shutdown()` hooks.

### 2. Config + DI (`quay.config`, `quay.di`)

`Settings` is a thin wrapper around `pydantic-settings`. It:

- Loads once at startup, re-validates on dev hot-reload.
- Exposes non-secret fields to the IR per `quay.toml`'s
  `[client] expose_settings = [...]` allowlist, so the generated TS
  client can know about feature flags without leaking secrets.

DI uses `Annotated[T, provider]`. Quay's addition is **scope**:
`_scope.py` providers attach to a subtree, so a provider declared in
`routes/users/_scope.py` is only resolved for routes under `/users/*`.

### 3. Plugin registry (`quay.plugins`)

Two discovery paths:

- **Entry points.** Anything declaring `quay.plugins` in its
  `[project.entry-points]` is auto-loaded at startup.
- **Explicit `register()`.** `src/app/plugins.py` can register adapters
  directly — useful when an extra `__init__` arg is needed (broker URL,
  credentials).

A plugin implements one or more **contracts**: `TaskAdapter`,
`Storage`, `KV`, `SessionStore`, `Mailer`, `Searchable`, `RateLimiter`,
`FeatureFlags`, `MetricsSink`, `LogSink`, `PubSub`, `AuthProvider`,
`DBSession`, … Each contract ships with a reference adapter in core (or
in a sibling repo for plugins that need a real dependency). Picking a
real backend is a one-line swap. Full mechanics in
[`plugins.md`](./plugins.md).

### 4. Background tasks (`quay.tasks`)

`@task` registers a handler into the IR and produces a callable that
adapters dispatch to:

```python
await send_welcome.enqueue(user_id)
```

The reference adapter is Dramatiq; alternatives (Celery, Arq, in-process)
implement the same protocol. The contract is small on purpose:

```python
class TaskAdapter(Protocol):
    async def enqueue(self, task: TaskRef, payload: bytes) -> str: ...
    async def schedule(self, task: TaskRef, when: datetime, payload: bytes) -> str: ...
    async def cron(self, task: TaskRef, expr: str) -> None: ...
    def eager(self) -> AsyncContextManager[None]: ...  # test mode
```

### 5. The dev loop (`quay.cli`)

`quay dev` runs the whole loop in one process:

1. Auto-discovery of `src/app/routes/` → registers handlers → triggers
   TS regeneration.
2. Hot-reload of `_middleware.py` and `_scope.py` without losing
   in-memory state where safe.
3. A diagnostics page at `http://localhost:8000/__quay` showing the
   route tree, registered tasks, current config (secrets redacted),
   plugin list, current OTel trace tail.
4. A rich error overlay (Starlette debug middleware enhanced with route
   context).

`quay build` produces a single artifact: the IR snapshot, the generated
`client.ts`, and a deployable Python wheel.

## Why this shape

A few decisions worth calling out explicitly.

**Why brackets in filenames?**
The cost is import semantics — `[id].py` can't be imported with
`from app.routes.users.[id] import ...`, so Quay loads it via
`importlib.util.spec_from_file_location()`. Cross-imports between route
files are rare in practice; when needed, Quay provides an explicit alias
mechanism. The benefit is the convention: bracket / paren / underscore
syntax is familiar from Next.js / Nuxt / SvelteKit and translates
cleanly to backend semantics.

**Why no built-in ORM / auth / mailer / admin?**
Every shipped opinion is a future pain point for the 60% of users who
already have a choice. Plugins make this opt-in. Core stays small,
upgradable, and replaceable.

**Why no AI / LLM primitives?**
The AI surface moves too fast for a framework to bake in. Threads,
agents, tool-calling, RAG chunking, evals — any choice we'd ship today
could be wrong in 18 months. Apps building AI features pick the library
that fits (LangGraph, Pydantic AI, Mastra) and consume Quay's
general-purpose primitives (`stream[T]`, `@task` for background
ingestion, the plugin contract for vector stores).

**Why depend on `dyadpy` for the typed-RPC layer?**
Type extraction, IR generation, TypeScript codegen, and SSE streaming
are a real piece of work on their own. `dyadpy` solves them well and
versions independently, which lets Quay focus on project shape (routing,
scopes, plugins, tasks) without re-implementing the wire layer. The
two compose cleanly: Quay registers handlers; the lower layer turns
them into a generated client.

## Where to read the code

- [`packages/quay/src/quay/routing/`](../packages/quay/src/quay/routing)
- [`packages/quay/src/quay/config.py`](../packages/quay/src/quay/config.py)
- [`packages/quay/src/quay/di.py`](../packages/quay/src/quay/di.py)
- [`packages/quay/src/quay/tasks.py`](../packages/quay/src/quay/tasks.py)
- [`packages/quay/src/quay/plugins.py`](../packages/quay/src/quay/plugins.py)
- [`packages/quay/src/quay/cli.py`](../packages/quay/src/quay/cli.py)

If you read all of those and still have a "wait, how does X work?"
question, that's a docs bug. Please file it.
