# API Reference

Every public symbol Causeway exports, on its own page. Organized by kind: decorators, functions, classes, file conventions, CLI.

> **Status:** v0.1 alpha. Public surface is what `causeway.__all__` declares. Anything not listed here may change in any release.

## Decorators

| Decorator              | Purpose                                                                  |
| ---------------------- | ------------------------------------------------------------------------ |
| [`@get`](./decorators/get.md)         | Register a function as a `GET` handler.                       |
| [`@post`](./decorators/post.md)       | Register a function as a `POST` handler.                      |
| [`@put`](./decorators/put.md)         | Register a function as a `PUT` handler.                       |
| [`@patch`](./decorators/patch.md)     | Register a function as a `PATCH` handler.                     |
| [`@delete`](./decorators/delete.md)   | Register a function as a `DELETE` handler.                    |
| [`@task`](./decorators/task.md)       | Mark a function as a background task.                         |
| [`@cron`](./decorators/cron.md)       | Schedule a function on a cron expression.                     |
| [`@provide`](./decorators/provide.md) | Declare a request-scoped DI provider in a `_scope.py`.        |
| [`@guard`](./decorators/guard.md)     | Lightweight middleware that runs before the handler.          |
| [`@raises`](./decorators/raises.md)   | Declare typed errors the handler may raise.                   |

## Functions

| Function                                                       | Purpose                                                            |
| -------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`create_app`](./functions/create-app.md)                      | Build the runnable ASGI app from a routes directory.               |
| [`register`](./functions/register.md)                          | Register a plugin adapter.                                         |
| [`env`](./functions/env.md)                                    | Return the current deployment environment.                         |
| [`configure_logging`](./functions/configure-logging.md)        | Set up structured logging.                                         |
| [`configure_otel`](./functions/configure-otel.md)              | Wire OpenTelemetry tracing.                                        |
| [`tasks_eager`](./functions/tasks-eager.md)                    | Run enqueued tasks inline (for tests).                             |
| [`discover`](./functions/discover.md)                          | Walk a routes directory and return a snapshot. (Low-level.)        |
| [`stream`](./functions/stream.md)                              | Marker for SSE return types: `stream[T]`.                          |
| [`raises`](./functions/raises.md)                              | Declare typed errors (re-exported from `dyadpy`).                  |
| [`Depends`](./functions/depends.md)                            | DI marker for handler params (re-exported from `dyadpy`).          |

## Classes

| Class                                                                       | Purpose                                                       |
| --------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [`Middleware`](./classes/Middleware.md)                                     | Protocol for class-based middleware.                          |
| [`Settings`](./classes/Settings.md)                                         | Re-export of `pydantic_settings.BaseSettings`.                |
| [`Manifest`](./classes/Manifest.md)                                         | Parsed `causeway.toml`.                                       |
| [`TestApp`](./classes/TestApp.md)                                           | In-process ASGI test client.                                  |
| [`RequestIdMiddleware`](./classes/RequestIdMiddleware.md)                   | ASGI middleware that stamps every request with an id.         |
| [`TaskRef`](./classes/TaskRef.md)                                           | Handle returned by `@task`.                                   |
| [`TaskState`](./classes/TaskState.md)                                       | Snapshot returned by `TaskAdapter.status`.                    |
| [`Contracts`](./classes/contracts.md)                                       | Plugin contract Protocols (`Storage`, `KV`, …).               |
| [`Errors`](./classes/errors.md)                                             | Built-in `HttpError` subclasses.                              |

## File conventions

| Convention                                                                 | What it means                                                  |
| -------------------------------------------------------------------------- | -------------------------------------------------------------- |
| [`index.py`](./file-conventions/index-py.md)                               | The folder's URL itself.                                       |
| [`[name].py`](./file-conventions/bracket-name.md)                          | Dynamic segment (folder style).                                |
| [`$name`](./file-conventions/dollar-name.md)                               | Dynamic segment (dot-flat style).                              |
| [`(group)/`](./file-conventions/group.md)                                  | Route group — folder stripped from URL.                        |
| [`_middleware.py`](./file-conventions/middleware-py.md)                    | Per-subtree middleware list.                                   |
| [`_scope.py`](./file-conventions/scope-py.md)                              | Per-subtree DI providers and lifespan hooks.                   |
| [`causeway.toml`](./file-conventions/causeway-toml.md)                     | Framework manifest.                                            |

## CLI

| Command                                                                | Purpose                                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`causeway new <name>`](./cli/new.md)                                  | Scaffold a new app.                                                |
| [`causeway dev`](./cli/dev.md)                                         | Run the dev server + watcher + codegen + diagnostics.              |
| [`causeway build`](./cli/build.md)                                     | Emit the IR, the TS client, and a deployable wheel.                |
| [`causeway plugins`](./cli/plugins.md)                                 | List registered plugin adapters.                                   |
| [`causeway plugin new <name>`](./cli/plugin-new.md)                    | Scaffold a new plugin package.                                     |
| [`causeway diff <a> <b>`](./cli/diff.md)                               | Compare two IR snapshots and flag breaking changes.                |
| [`causeway deploy <target>`](./cli/deploy.md)                          | Invoke the relevant deploy plugin.                                 |
| [`causeway version`](./cli/version.md)                                 | Print the installed version.                                       |

## Module map

| Module                    | Contents                                                                  |
| ------------------------- | ------------------------------------------------------------------------- |
| `causeway`                | Public re-exports (`get`, `post`, `task`, `register`, …).                 |
| `causeway.errors`         | `HttpError` and subclasses, problem+json renderer.                        |
| `causeway.middleware`     | `Middleware` Protocol, `Request`, `Response`, `guard`.                    |
| `causeway.routing`        | `discover`, `register`, `Discovered`, `DiscoveredRoute` (low-level).      |
| `causeway.tasks`          | `task`, `cron`, `TaskRef`, `TaskState`, `InMemoryAdapter`.                |
| `causeway.testing`        | `TestApp`, `expect`, `scenario`, `snapshot`, `stub`, `tasks_eager`.       |
| `causeway.config`         | `Settings`, `Manifest`, `load_settings`, `load_manifest`.                 |
| `causeway.contracts`      | Plugin Protocols (`Storage`, `KV`, `Mailer`, `TaskAdapter`, …).           |
| `causeway.plugins`        | `register`, `env`, `registered`, `discover` (entry-point loader).         |
| `causeway.adapters`       | Reference implementations (`LocalStorage`, `MemoryKV`, …).                |
| `causeway.observability`  | `RequestIdMiddleware`, `configure_logging`, `configure_otel`.             |
