# Code map

Every module in `packages/causeway/src/causeway/`, in roughly the order you'd read them on a first pass. Line counts are the actual size, not target sizes — the framework is small on purpose, but nobody's chasing a number.

Underscore-prefixed modules are internal (`_paths.py`, `_methods.py`, etc.) — they're allowed to break across patches. Anything without an underscore prefix is part of the stable surface after 1.0.

---

## The public surface

### `__init__.py` — 68 lines

The public API re-export wall. Everything an application author types `from causeway import ...` for lives here:

- HTTP method decorators (`get`, `post`, `put`, `patch`, `delete`) — re-exported from `_methods.py`.
- `Middleware`, `guard` — from `middleware.py`.
- `provide` — from `scope.py`.
- `task`, `cron`, `tasks_eager` — from `tasks.py`.
- `Settings`, `Manifest` — from `config.py`.
- `register`, `env` — from `plugins.py`.
- `RequestIdMiddleware`, `configure_logging`, `configure_otel` — from `observability.py`.
- `create_app` — from `app.py`.

When you add a new public symbol, **add it here too**. That's the contract.

### `app.py` — 98 lines

`create_app(routes_root, *, plugins=None, settings=None, manifest=None)` — the factory. Walks the routes tree, registers handlers, wires lifespan hooks, attaches health endpoints, returns a `dyadpy.App`. This is the thing `causeway dev` and your `pytest` fixtures both call.

### `config.py` — 107 lines

`Settings` is a re-export of `pydantic_settings.BaseSettings` (with an explicit annotation so type checkers see a complete type even when pydantic-settings ships without a `py.typed`). `Manifest` reads `causeway.toml` and exposes `[client] expose_settings = [...]` — the allowlist for fields surfaced to the generated TS client. `expose_for_client(settings, manifest)` does the filtering, also dropping any `SecretStr` / `SecretBytes` fields so secrets can't leak even if you list them.

---

## Routing

### `_paths.py` — 116 lines

URL-pattern translation. Pure functions, no I/O.

`url_for(rel_path)` takes a route file's relative path (`users/[id]/posts.py`) and returns the URL pattern (`/users/{id}/posts`). Handles both **folder style** (`[id]`, `(group)`, `index.py`) and **dot-flat style** (`users.$id.index.py`, `(admin).stats.py`) — and mixed (`api/v1.$version.posts.py`).

The leaf tokenizer is a regex (`_LEAF_TOKEN`) that splits on `.` but keeps `[...]` and `(...)` segments intact, so `[...rest]` doesn't get torn apart by the dot splitter.

### `routing.py` — 360 lines

The walker, the loader, the binder. The biggest module in core, and the one most worth reading first.

Three phases:

1. **`discover(routes_root)`** — recursive walk, builds `Discovered` (routes + middleware + lifespan hooks). Skips underscore-prefixed files. Handles `_middleware.py` and `_scope.py` as per-subtree composition. Detects method conflicts.
2. **`register(app, found)`** — binds the discovered handlers onto a `dyadpy.App` via `@get` / `@post` decorators on the right paths.
3. **`_bind_providers` / `_compose_guards`** — wraps each handler with its provider chain (`Annotated[T, get_session]`) and guard chain (lightweight middleware functions).

Three subtleties worth knowing if you're touching this file:

- Modules are loaded with `importlib.util.spec_from_file_location`. The synthetic module name is `causeway._routes.<hash>` so dotted / bracketed filenames don't confuse Python's import system.
- Provider matching is by `(source_location, name)` — `[id]` files can be reloaded without losing provider identity.
- The handler wrapper preserves dyadpy's view of the original signature (`__wrapped__`, `__annotations__`, `__globals__`) so string forward-refs resolve correctly when dyadpy inspects the wrapper.

### `_methods.py` — 42 lines

Tiny shim that exposes the HTTP method decorators in a way that's friendly to both `@get` (no path arg — path comes from file location) and `@get("/explicit")` (legacy / escape hatch).

### `scope.py` — 41 lines

`provide(name)` — the request-scoped DI provider decorator. Tracks provider source location so the router can dedupe across re-imports.

### `middleware.py` — 53 lines

`Middleware` ABC and `@guard` decorator (lightweight function-style middleware). Re-exports `Request` and `Response` from Starlette so users can type their middleware against them.

---

## Plugins

### `contracts.py` — 218 lines

Every official contract as a `typing.Protocol`. `Plugin`, `TaskAdapter`, `Storage`, `KV`, `Mailer`, `AuthProvider`, `DBSession`, `BlobScanner`, `FeatureFlags`, `MetricsSink`, `LogSink`, `PubSub`, `RateLimiter`, `SessionStore`, `DeployTarget`. Each contract declares `contract_version: ClassVar[str] = "v1.0"`.

If you're adding a new official contract, **start here**. Then add a reference adapter in `adapters.py` (or punt to a sibling package), and a test that round-trips against the protocol.

### `plugins.py` — 235 lines

The registry. Two discovery paths feed one ordered dict:

- **Entry-point discovery** (`discover("causeway.plugins")`) — auto-loads any installed package that declares a `causeway.plugins` entry point.
- **Explicit `register(adapter)`** — for adapters that need constructor args.

Lifecycle: `startup_all(settings)` fires every plugin's `startup` in registration order; `shutdown_all()` fires `shutdown` in reverse. `check_required_contracts()` walks `requires` lists and refuses to boot if a dependency is missing. `merge_settings_fragments(settings)` applies each plugin's optional `settings_fragment()` to the `Settings` instance.

### `adapters.py` — 305 lines

Reference adapters shipped in core: `MemoryKV`, `LocalStorage`, `MemoryLimiter`, `StaticFlags`, `NullSink`, `MemoryBus`, `NullScanner`. These exist so the framework boots out of the box; production users swap them via a sibling `causeway-*` package.

---

## Background tasks

### `tasks.py` — 328 lines

`@task`, `@cron`, `TaskRef`, `tasks_eager()`, and `InMemoryAdapter` (the reference). The module also holds the active-adapter `ContextVar` so test-mode can swap in eager dispatch without leaking across concurrent tests.

### `_cron.py` — 65 lines

5-field crontab parser used by `InMemoryAdapter._cron_loop`. Pure function, fully tested. Production adapters (Dramatiq, Celery) delegate to a real scheduler instead.

---

## Cross-cutting

### `observability.py` — 142 lines

`RequestIdMiddleware` stamps every request with a stable id and echoes it as `X-Request-Id`. `configure_logging(json=True/False)` sets up structlog. `configure_otel(...)` and `instrument_asgi(app)` lazy-import OpenTelemetry — both are no-ops when the `otel` extra isn't installed.

### `errors.py` — 135 lines

`HttpError` hierarchy (`NotFound`, `BadRequest`, `Unauthorized`, `Forbidden`, …) and the global handler that renders them as RFC 7807 `application/problem+json`. The handler **never** leaks internal exception messages — the body for an uncaught exception is the generic `internal server error`. Subclass `HttpError` to opt into a custom message.

### `health.py` — 54 lines

`/healthz` (process up) and `/readyz` (every plugin's `ready()` returns true). `attach(app)` wires them; the dev loop and `create_app` both call it.

### `diagnostics.py` — 93 lines

The `/__causeway` endpoint. Builds a JSON snapshot — route tree, registered tasks, cron jobs, plugins, non-secret config — for the dev panel.

### `testing.py`

`TestApp.from_routes(routes_root)` / `TestApp.wrap(app)`, an httpx-based async client, `.override(provider, replacement)` for swapping DI providers in tests, `stub(provider, value)` for the common "just return this value" case, and a re-export of `tasks_eager()` for symmetry. Also re-exports the inline-scenario API (`scenario`, `expect`, `snapshot`, `Response`, `Expectation`, `ScenarioAssertionError`, `SnapshotValue`).

### `_testing/`

The inline-scenario runtime. Lives in a private subpackage so the implementation can evolve without touching the public `testing.py` surface.

- `scenario.py` — `scenario(...)` context manager and the synchronous `_It` client that drives httpx-over-ASGI through a per-scenario event loop.
- `expect.py` — `expect(...)` proxy with operator-overloaded assertions and path-aware diff messages.
- `response.py` — `Response` + `PathValue`, the attribute/item walker for JSON bodies.
- `snapshot.py` — `snapshot(...)` marker, ellipsis-aware structural match, pending-edit registry.
- `rewrite.py` — tokenize-based source rewriter used when `--update-snapshots` is set.
- `loader.py` — imports a route file with `__name__ == "__causeway_test__"` by compiling + execing source directly (bypasses importlib's name-match check).
- `registry.py` — contextvar plumbing the plugin uses to publish a `Registry` into the imported module.
- `discover.py` — finds routes roots by walking up for `causeway.toml` siblings, with a shallow `app/routes` fallback.
- `errors.py` — `ScenarioAssertionError(AssertionError)` with rendered unified diffs.

### `_pytest_plugin.py`

Registered via the `pytest11` entry point. Adds `--causeway-routes`, `--update-snapshots`, `--causeway-no-inline`; matches route files via `pytest_collect_file`; yields one `ScenarioItem` per `scenario(...)` block; applies snapshot rewrites in `pytest_sessionfinish`.

### `cli.py` — 227 lines

The `causeway` CLI built on Typer. Commands: `new` (scaffold via `_scaffold.py`), `dev` (uvicorn + watcher), `build` (codegen + wheel), `plugins` (list registered adapters), `diff` (IR breaking-change detection via `dyadpy diff`), `deploy <target>` (dispatch to a registered `DeployTarget`), `plugin new <name>` (scaffold a new plugin package).

### `_scaffold.py` — 261 lines

Templates for `causeway new` and `causeway plugin new`. The longest non-routing module, almost entirely string literals.

---

## Tests

Every public module has a test file with the same name: `tests/test_routing_register.py`, `tests/test_paths.py`, `tests/test_plugins.py`, `tests/test_tasks.py`, etc. The pattern is:

- One test file per source module.
- pytest, `asyncio_mode = "auto"` (so `async def test_…` works without a marker).
- `filterwarnings = ["error"]` (warnings fail tests; we want to know).

When you fix a bug, add a regression test next to its module's test file. When you add a public API, add at least one test for it.
