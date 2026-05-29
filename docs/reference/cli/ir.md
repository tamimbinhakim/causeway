# `causeway ir`

Emit the route IR as JSON.

```bash
causeway ir app:app --out causeway-ir.json
```

## Synopsis

```
causeway ir [module] [--out <file>]
```

## Arguments

| Argument | Default   | Description                      |
| -------- | --------- | -------------------------------- |
| `module` | `app:app` | ASGI app import path to inspect. |

## Options

| Option         | Default            | Description       |
| -------------- | ------------------ | ----------------- |
| `--out` / `-o` | `causeway-ir.json` | Output JSON path. |

## IR vs Graph

Use `causeway ir` when you care about the wire contract: route params, bodies, responses, errors, and settings exposed to the client.

Use `causeway inspect --json` when you care about application shape: source files, scopes, middleware, providers, refreshes, tasks, plugins, and events.

## See Also

- [IR flow](../../architecture/ir-flow.md)
- [IR stability](../../stability/ir-stability.md)
- [`inspect`](./inspect.md)
