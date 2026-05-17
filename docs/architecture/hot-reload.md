# Hot reload

How the dev loop handles `.py` saves without losing state where it can preserve it.

## What `causeway dev` does

```bash
causeway dev
```

is roughly:

```
uvicorn app:app --reload --reload-includes='*.py'
```

— with a few extras layered on:

1. The app factory pattern means each reload calls `create_app(...)` from scratch — routes re-discover, scopes re-bind.
2. The dyadpy watcher tails the route tree and re-emits `client.ts` on every save.
3. The module cache (`causeway.routing._module_cache`) gets reset between reloads via `reset_module_cache()` so re-imports pick up fresh source.

## What's preserved across reloads

- **Plugin connections.** `register(...)` calls run in `plugins.py`; on reload the registry rebuilds, but you control what shuts down via `shutdown()` on each adapter. Reuse Redis pools, S3 sessions, etc., if your adapter is idempotent on startup.
- **OS-level resources.** TCP sockets that uvicorn opens stay open.

## What's lost

- **In-process state** that lives in module-level globals. A counter you incremented? Gone.
- **In-flight requests.** Uvicorn drains gracefully but doesn't preserve sessions.
- **`@task` adapter state** (with `InMemoryAdapter`). Use a real broker for anything that has to survive a code change.

If you want state that survives reloads:
- Put it behind a `_scope.py` `startup()` that's idempotent.
- Use an external store (Redis, Postgres) accessed via a plugin.

## Why a process reload at all

Uvicorn's `--reload` runs the app inside a child process and replaces the child on every change. This is the only reliable way to evict Python module caches in CPython — `importlib.reload` can leave stale references in unrelated modules.

The trade-off is a sub-second restart on every save, vs. correctness gaps that surface days later. We pick correctness.

## Watch list

By default, every `.py` under the project root is watched. To watch additional file types (templates, YAML config):

```bash
uvicorn app:app --reload --reload-includes='*.py' --reload-includes='*.yaml'
```

Or wire it into your own dev script — `causeway dev` is a convenience over uvicorn, not a hard wrapper.

## Debugging reload loops

Symptoms: file save → reload → reload → reload (loop).

Common cause: a file that the reload process itself writes (e.g. a regenerated `client.ts`). Add it to `--reload-excludes`:

```bash
uvicorn app:app --reload --reload-excludes='client.ts'
```

## See also

- [Boot pipeline](./boot-pipeline.md)
- [`dev`](../api-reference/cli/dev.md)
