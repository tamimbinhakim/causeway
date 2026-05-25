# `causeway dev`

Run the owned dev server: uvicorn once, smart route hot-swap, route-aware
terminal logs, and diagnostics page.

```bash
causeway dev
```

## Synopsis

```
causeway dev [--module <path>] [--host <host>] [--port <port>]
```

## Options

| Option     | Default       | Description           |
| ---------- | ------------- | --------------------- |
| `--module` | `"app:app"`   | ASGI app import path. |
| `--host`   | `"127.0.0.1"` | Bind host.            |
| `--port`   | `8000`        | Bind port.            |

## What it does

1. Sets `CAUSEWAY_ENV=dev` if not already set.
2. Boots uvicorn once behind Causeway's hot-swap ASGI wrapper.
3. Watches Python files under the project root.
4. Route changes rebuild a new app snapshot, rediscover routes, then atomically
   swap it in. Failed reloads keep the previous snapshot serving.
5. Lifecycle/global Python changes print `restart required` instead of doing an
   unsafe partial reload.
6. Mounts `/healthz`, `/readyz`, `/__causeway` (diagnostics page).

## Diagnostics page

Open <http://127.0.0.1:8000/__causeway>:

- Route tree (handler source paths, declared errors, providers in scope).
- Registered plugins (contract version, module).
- Current settings (secrets redacted).
- Recent logs and traces (if OTel is wired).

This is the fastest way to know what Causeway thinks of your app.

## Hot reload

Saved route changes do not restart the process. In-flight requests continue on
the previous snapshot; new requests use the new snapshot after a successful
reload. Plugin connections and other process-local resources stay alive.

Changes outside the route tree, and `_scope.py` files that declare
`startup()`/`shutdown()`, are marked `restart required` because lifecycle hooks
need a clean startup/shutdown cycle.

## See also

- [Project structure](../../getting-started/project-structure.md)
- [`build`](./build.md) — production artifact.
