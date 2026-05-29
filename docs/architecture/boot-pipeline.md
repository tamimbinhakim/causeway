# Boot pipeline

What happens between `causeway dev` and your first request.

## Step by step

```
1. CLI starts (causeway dev)
       ↓
2. uvicorn imports `app:app`  (or whatever --module points at)
       ↓
3. causeway.toml is parsed (Manifest)
       ↓
4. app.config is imported → Settings() instantiated
       ↓
5. Entry-point plugins auto-load
   (each calls register(...) via its `plugin(settings)` callable)
       ↓
6. app.plugins is imported → explicit register(...) calls run
       ↓
7. create_app(routes_root, settings=settings) is called
       │
       ├─ discover(routes_root)
       │     ├─ walks the tree
       │     ├─ loads every _middleware.py and _scope.py per directory
       │     ├─ imports every .py route file
       │     ├─ collects @get/@post/...-decorated handlers
       │     ├─ rewrites Annotated[T, provider] → Depends(provider)
       │     └─ returns a Discovered snapshot
       │
       ├─ register(inner_app, discovered)
       │     └─ wires each route onto the inner causeway.App
       │
       ├─ build App Graph
       │     └─ routes, route keys, scopes, middleware, providers, plugins, tasks, events
       │
       ├─ attach health endpoints (/healthz, /readyz)
       ├─ attach diagnostics (/__causeway and dev-only /__causeway/graph) if enabled
       ├─ install RequestIdMiddleware at the boundary
       ├─ install each class Middleware collected from _middleware.py files
       └─ install the problem+json error renderer
       ↓
8. Starlette wraps the inner runtime App + middleware chain + lifespan
       ↓
9. Lifespan starts
       ├─ plugin startup() in registration order
       │     └─ check_required_contracts() — fail fast if a plugin's `requires` aren't met
       │     └─ merge_settings_fragments(settings)
       │     └─ for each adapter: await adapter.startup(settings)
       ├─ _scope.py startup() in discovery order
       └─ ready
       ↓
10. uvicorn serves traffic
       ↓
11. causeway dev watches route files and hot-swaps a new app snapshot after
    successful rediscovery
```

## What discover does in detail

For each directory under `routes_root`:

1. Load `_middleware.py` if present, validate every entry is a `Middleware` or `@guard`-decorated function.
2. Load `_scope.py` if present, collect every `@provide("name")`-decorated function, read optional `startup` / `shutdown`.
3. Merge with the inherited frame (parent scope) — providers compose, inner-most wins.
4. For each `.py` file that isn't underscore-prefixed:
   - Compute the URL via `url_for(rel_path)`.
   - Compute the route key via `route_key_for(method, rel_path)`.
   - Collect route-group scopes via `scope_groups_for(rel_path)`.
   - Import the file.
   - Find every `@get`/`@post`/...-decorated handler.
   - Append a `DiscoveredRoute` with its method, path, route key, handler, middleware list, providers, refreshes, metadata, and source path.
5. Recurse into non-underscore subdirectories.

After the walk:

- `_check_method_conflicts` raises if two handlers resolve to the same `(method, path)`.
- For each route, `_bind_providers` rewrites `Annotated[T, provider]` to `Depends(provider)`.
- For each route, `_compose_guards` wraps the handler to run guards before the body and attaches class middleware via `__causeway_class_middleware__` for the ASGI layer.
- `shutdown_hooks` is reversed so outer-most teardown runs last.

## Imports are cached by physical path

The router uses a module cache keyed by the resolved physical path so re-importing the same `_scope.py` from different code paths returns the same Python module. This matters for provider identity — `_bind_providers` matches providers by source location + qualname, not by Python identity, but having the same module instance keeps everything aligned.

`reset_module_cache()` exists for the hot-reload path.

## Class middleware vs guards

A `_middleware.py` may export both. The walker separates them:

- **`@guard` functions** are wrapped around each handler inline (via `_compose_guards`). They run before the handler body in the same async task.
- **Class `Middleware` instances** are attached to the handler via `__causeway_class_middleware__`. `create_app` walks every discovered route and registers each unique instance as a `BaseHTTPMiddleware`-wrapped Starlette middleware at the app level.

This split is why guards have access to the runtime's request `Context` while class middleware sees the raw ASGI scope.

## See also

- [Code map](../internals/code-map.md) — file-by-file source tour.
- [IR flow](./ir-flow.md)
- [Hot reload](./hot-reload.md)
