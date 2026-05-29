# `causeway inspect`

Inspect the Causeway App Graph.

```bash
causeway inspect
causeway inspect --json
```

## Synopsis

```
causeway inspect [module] [--json]
```

## Arguments

| Argument | Default   | Description                      |
| -------- | --------- | -------------------------------- |
| `module` | `app:app` | ASGI app import path to inspect. |

## Options

| Option   | Description               |
| -------- | ------------------------- |
| `--json` | Print raw App Graph JSON. |

## Output

Without `--json`, Causeway prints a compact route table with method, route key, HTTP path, and refreshes.

With `--json`, it prints the full graph: routes, source files, scopes, params, responses, errors, streams, refreshes, middleware, providers, permission metadata, idempotency metadata, plugins, tasks, and events.

## See Also

- [App Graph](../../client/app-graph.md)
- [Client runtime](../../client/index.md)
