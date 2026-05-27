# Hot reload

How the dev loop handles `.py` saves without restarting the server process.

## What `causeway dev` does

```bash
causeway dev
```

starts uvicorn once around a Causeway-owned hot-swap ASGI wrapper:

```
uvicorn -> HotSwapApp -> current app snapshot
```

On boot, Causeway imports your app, discovers the route tree, starts normal
lifespan resources, and begins watching Python files. On a route edit it:

1. batches file-system events for a short debounce window,
2. resets Causeway's route-module cache,
3. re-imports the app entry module,
4. re-discovers routes,
5. swaps the new snapshot in only if the rebuild succeeds.

In-flight requests keep using the old snapshot. New requests use the new
snapshot immediately after the swap.

## What's preserved

- **The server process and socket.** Uvicorn is not restarted for route edits.
- **In-flight requests.** A request that started before the swap finishes on the
  old snapshot.
- **Plugin connections and process-local resources.** The initial app lifespan
  owns startup/shutdown; route edits do not tear down DB pools, Redis clients,
  task adapters, or in-memory dev state.

## Failed reloads

If a route edit has a syntax error, bad import, bad annotation, or route
conflict, Causeway prints a short diagnostic and keeps serving the previous app:

```text
reload failed - serving previous app

SyntaxError: expected ':'
trace:
  app/routes/users/$id.py:14 in <module>
    async def show(id: UUID) -> User
full traceback: set CAUSEWAY_FULL_TRACEBACK=1
```

Causeway keeps these diagnostics narrow enough to survive prefixed dev
terminals, such as monorepo scripts that prepend `api:dev:` to every line. Set
`CAUSEWAY_TRACEBACK_WIDTH=120` if you want a wider panel.

## Restart-required changes

Some changes intentionally do not hot-swap:

- Python files outside the route tree, such as `app/plugins.py`,
  `app/lifespan.py`, or config modules.
- `_scope.py` files that declare `startup()` or `shutdown()`.

Those files can change lifecycle resources. Causeway prints `restart required`
instead of doing a misleading partial reload.

## Terminal output

The dev server reports each reload transaction:

```text
Causeway dev

  server     http://127.0.0.1:8000
  app        app:app
  routes     app/routes  18 routes
  reload     smart hot-swap

[12:41:08] changed   app/routes/users/$id.py
[12:41:08] reload ok 43ms  generation=7  routes=18
  ~ GET    /users/{id}  app/routes/users/$id.py
```

Access logs are short too:

```text
[12:41:11] GET    /users/42       200  5ms
[12:41:12] POST   /login          401  3ms
```

## See also

- [Boot pipeline](./boot-pipeline.md)
- [`dev`](../api-reference/cli/dev.md)
