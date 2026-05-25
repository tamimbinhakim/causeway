# Architecture

This is what's actually happening when you type `causeway dev`. It's not magic,
and the parts are small enough that you can read the whole thing in a
weekend.

> **One-line acknowledgement.** Causeway's typed-RPC layer — the IR format,
> the TypeScript codegen, the streaming envelope — is provided by `dyadpy`,
> a lower-level primitive that Causeway depends on. Everything below
> describes Causeway's surface; the IR / codegen plumbing under it is mostly
> Dyadpy doing its job. From an application author's perspective: it's
> all Causeway.

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
  _middleware.py          causeway.toml manifest
  _scope.py                    │
        │                      ▼
        ▼                  Generated client/
   Scoped DI graph
```

Two flows: **server start** walks the `routes/` tree and registers
everything into the IR; **at request time** the ASGI runtime composes
middleware + scopes + handler from the precomputed graph.

## Layer by layer

### 1. File-based router (`causeway.routing`)

The router walks `src/app/routes/**/*.py`, ignoring underscore-prefixed
files (those are private). For each file:

1. Translate the filename + path into a URL pattern. `$id.py` becomes
   `{id}`, `(group)/` is stripped, `index.py` is the folder URL.
2. Load the module via `importlib.util.spec_from_file_location()` — this
   is how `$` filenames work without breaking Python's import system.
3. Find handler exports decorated with `@get` / `@post` / etc., and
   register them into the route table.

Two file conventions are special:

- `_middleware.py` — its `middleware = [...]` list wraps every route in
  the same subtree.
- `_scope.py` — its `provide(...)` registrations are available to every
  handler in the subtree, request-scoped, plus optional `startup()` /
  `shutdown()` hooks.

### 2. Config + DI (`causeway.config`, `causeway.di`)

`Settings` is a thin wrapper around `pydantic-settings`. It:

- Loads once at startup, re-validates on dev hot-reload.
- Exposes non-secret fields to the IR per `causeway.toml`'s
  `[client] expose_settings = [...]` allowlist, so the generated TS
  client can know about feature flags without leaking secrets.

DI uses `Annotated[T, provider]`. Causeway's addition is **scope**:
`_scope.py` providers attach to a subtree, so a provider declared in
`routes/users/_scope.py` is only resolved for routes under `/users/*`.

### 3. Plugin registry (`causeway.plugins`)

Two discovery paths:

- **Entry points.** Anything declaring `causeway.plugins` in its
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

### 4. Background tasks (`causeway.tasks`)

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

### 5. The dev loop (`causeway.cli`)

`causeway dev` runs the whole loop in one process:

1. Auto-discovery of `src/app/routes/` → registers handlers.
2. Smart route hot-swap without restarting uvicorn: rebuild a new app snapshot,
   then atomically swap it in after validation. In-flight requests stay on the
   previous snapshot.
3. A diagnostics page at `http://localhost:8000/__causeway` showing the
   route tree, registered tasks, current config (secrets redacted),
   plugin list, current OTel trace tail.
4. Rich terminal logging for route diffs, reload failures, restart-required
   files, and short request lines.

`causeway build` produces the release artifacts: the IR snapshot, the generated
`client/` directory, and a deployable Python wheel.

## Why this shape

A few decisions worth calling out explicitly.

**Why `$` in filenames?**
The cost is import semantics — `$id.py` can't be imported with
`from app.routes.users.$id import ...`, so Causeway loads it via
`importlib.util.spec_from_file_location()`. Cross-imports between route
files are rare in practice; when needed, Causeway provides an explicit alias
mechanism. The benefit is one dynamic-route convention that works in both
folder style (`users/$id.py`) and dotted leaves (`users.$id.posts.py`).

**Why no built-in ORM / auth / mailer / admin?**
Every shipped opinion is a future pain point for the 60% of users who
already have a choice. Plugins make this opt-in. Core stays small,
upgradable, and replaceable.

**Why depend on `dyadpy` for the typed-RPC layer?**
Type extraction, IR generation, TypeScript codegen, and SSE streaming
are a real piece of work on their own. `dyadpy` solves them well and
versions independently, which lets Causeway focus on project shape (routing,
scopes, plugins, tasks) without re-implementing the wire layer. The
two compose cleanly: Causeway registers handlers; the lower layer turns
them into a generated client.

## Where to read the code

- [`packages/causeway/src/causeway/routing/`](../packages/causeway/src/causeway/routing)
- [`packages/causeway/src/causeway/config.py`](../packages/causeway/src/causeway/config.py)
- [`packages/causeway/src/causeway/di.py`](../packages/causeway/src/causeway/di.py)
- [`packages/causeway/src/causeway/tasks.py`](../packages/causeway/src/causeway/tasks.py)
- [`packages/causeway/src/causeway/plugins.py`](../packages/causeway/src/causeway/plugins.py)
- [`packages/causeway/src/causeway/cli.py`](../packages/causeway/src/causeway/cli.py)

If you read all of those and still have a "wait, how does X work?"
question, that's a docs bug. Please file it.
