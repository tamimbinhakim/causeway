# Alpha → 0.1.0

What to expect when the first non-alpha tag ships.

> **Status:** 0.1.0 is not yet released. This page is forward-looking — it'll be filled in with concrete diffs once 0.1.0 is cut.

## The plan

0.1.0 is the **API freeze for v0.1**. From 0.1.0 onwards:

- Every symbol in `causeway.__all__` is part of the public surface.
- Every contract in `causeway.contracts` carries `contract_version = "v1.0"`.
- Every public file convention (`_middleware.py`, `_scope.py`, `$name.py`, `$name/`) is locked.

Between 0.1.0 and 1.0 we'll add features without removing or renaming the existing ones — but pre-1.0, that promise is informal. After 1.0, it's enforced by [`semver`](../stability/semver.md).

## What may change before 0.1.0

- **`stream[T]` plus the runtime's stream codegen** — currently SSE-only; bidirectional streaming is a candidate to slip in.
- **Catch-all segments (`$$rest`)** — currently raise `NotImplementedError`. They land in 0.2+, not 0.1.
- **Inline scenarios DSL** — `expect` and `snapshot` may get richer matchers.

## What is locked

- Method decorators (`@get`, `@post`, `@put`, `@patch`, `@delete`).
- File conventions for routing (`index.py`, `$name.py`, `$name/`, `(group)/`).
- Scope + middleware conventions (`_scope.py`, `_middleware.py`).
- Task + cron decorators (`@task`, `@cron`).
- The `Plugin` lifecycle (`startup`, `ready`, `shutdown`).
- `RequestIdMiddleware` and the problem+json error renderer.

## Migration tools

`causeway diff` will flag any breaking change between two builds — point it at your previous release's `ir.json` after upgrading to confirm nothing in your app's surface changed by accident.

## See also

- [`semver`](../stability/semver.md)
- [`CHANGELOG.md`](../../CHANGELOG.md)
- [Upgrading overview](./index.md)
