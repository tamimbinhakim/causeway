# `causeway dev`

Run the dev server: `uvicorn` + file watcher + TS codegen + diagnostics page.

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
2. Boots `uvicorn` with `--reload` (file watcher built in).
3. The app factory re-runs on every reload — `routes/` is re-discovered, `client.ts` is re-emitted.
4. Mounts `/healthz`, `/readyz`, `/__causeway` (diagnostics page).

## Diagnostics page

Open <http://127.0.0.1:8000/__causeway>:

- Route tree (handler source paths, declared errors, providers in scope).
- Registered plugins (contract version, module).
- Current settings (secrets redacted).
- Recent logs and traces (if OTel is wired).

This is the fastest way to know what Causeway thinks of your app.

## Hot reload

`uvicorn --reload` watches every `.py` under the working directory. Saved changes restart the process — Causeway re-discovers routes, re-emits the client, re-binds providers. State that lives in-process is lost on reload (use `_scope.py` startup hooks for things that should survive).

## See also

- [Project structure](../../getting-started/project-structure.md)
- [`build`](./build.md) — production artifact.
