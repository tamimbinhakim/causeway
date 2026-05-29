# Project structure

A Causeway app has a small, fixed shape. Once you know where things live, you stop thinking about it.

## What `causeway new` creates

```
my-app/
├── pyproject.toml
├── causeway.toml                # framework manifest — what the TS client sees
├── .env / .env.example          # local secrets
└── src/app/
    ├── __init__.py
    ├── config.py                # Settings(BaseSettings) — typed config
    ├── plugins.py               # register(DramatiqAdapter(...)), etc.
    ├── lifespan.py              # optional app-level startup / shutdown
    ├── routes/
    │   ├── _middleware.py       # wraps every route below this folder
    │   └── index.py             # GET /
    └── events/
        └── example.created.py   # listeners for the `example:created` event
```

Nothing in that tree is sacred — delete files you don't need, add the ones you do. The router only cares about what's under `src/app/routes/`.

## The files that matter

| Path                  | What it is                                                                                               |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| `causeway.toml`       | Manifest. `[client] expose_settings = [...]` is the allowlist for what flows to the TS client.           |
| `src/app/config.py`   | Your `Settings(BaseSettings)` subclass and a `settings = Settings()` instance.                           |
| `src/app/plugins.py`  | `register(...)` calls for adapter plugins (tasks, storage, auth, …).                                     |
| `src/app/lifespan.py` | Optional async `startup` / `shutdown` hooks for the whole app.                                           |
| `src/app/routes/`     | The route table. Folder layout is the URL layout.                                                        |
| `src/app/events/`     | Event listeners. Filename → event name; every `async def` is a listener. See [Events](../app/events.md). |

## The route directory

The router walks `src/app/routes/` once at boot and registers every handler it finds. Within the tree, three filename conventions are special:

| File             | Role                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| `_middleware.py` | Wraps every route in the current subtree. Composes outermost → leaf. |
| `_scope.py`      | Declares request-scoped DI providers + optional lifespan hooks.      |
| `_*.py`, `_*/`   | Private — colocated helpers, never routed.                           |

Anything else under `routes/` that ends in `.py` is a route file. The path becomes the URL via the [file conventions](../reference/file-conventions/index.md).

## Where Python knows about your app

`pyproject.toml` declares your package layout:

```toml
[project]
name = "my-app"
version = "0.0.1"
requires-python = ">=3.11"
dependencies = ["causeway==0.1.0a0"]

[tool.hatch.build.targets.wheel]
packages = ["src/app"]
```

Causeway expects to import your app as `app`. If you rename it, pass `--module` to `causeway dev`.

## What the dev loop actually does

`causeway dev` runs:

1. Walks `src/app/routes/` and registers every handler.
2. Boots `uvicorn` once behind Causeway's smart hot-swap wrapper.
3. Builds the App Graph: route keys, HTTP paths, source files, scopes,
   middleware, permissions, refresh contracts, providers, tasks, plugins, and
   events.
4. Mounts `/healthz`, `/readyz`, `/__causeway` (diagnostics), and in dev
   `/__causeway/graph`.
5. Hot-swaps route edits without restarting the process. Bad reloads keep the
   last good app running; lifecycle-sensitive edits print `restart required`.

On a clean boot you see one line per registered route. If a route is missing from `/__causeway`, the discovery rules in [Defining routes](../backend/routing.md) explain why.

## Route Layout

```
src/app/routes/
├── index.py                     # /
├── users/
│   ├── index.py                 # /users
│   └── $id.py                  # /users/{id}
└── billing/
    └── webhooks.py              # /billing/webhooks
```

Use folders for URL structure. Dotted route filenames are rejected so routes,
middleware, scopes, and generated route keys all follow the same convention.
See [Defining routes](../backend/routing.md) for the full rules.

The matching public route keys are:

| File                         | Handler | Route key                |
| ---------------------------- | ------- | ------------------------ |
| `routes/index.py`            | `@get`  | `GET /`                  |
| `routes/users/index.py`      | `@get`  | `GET /users`             |
| `routes/users/$id.py`        | `@get`  | `GET /users/$id`         |
| `routes/billing/webhooks.py` | `@post` | `POST /billing/webhooks` |

## Next steps

- [Your first route](./first-route.md)
- [First product slice](./first-slice.md)
- [Defining routes](../backend/routing.md)
