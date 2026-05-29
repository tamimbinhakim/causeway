# `causeway codegen`

Emit the generated TypeScript client directory without building a wheel.

```bash
causeway codegen app:app --out src/lib/causeway/client
```

## Synopsis

```
causeway codegen [module] [--out <dir>]
```

## Arguments

| Argument | Default   | Description                      |
| -------- | --------- | -------------------------------- |
| `module` | `app:app` | ASGI app import path to inspect. |

## Options

| Option         | Default                   | Description              |
| -------------- | ------------------------- | ------------------------ |
| `--out` / `-o` | `src/lib/causeway/client` | Output client directory. |

## Output

The directory contains the typed route-key client:

```
client/
├── index.ts
├── types.d.ts
├── meta.ts
└── routes/
```

Most apps use `causeway build`, which runs codegen and also produces the wheel. Use `codegen` directly when your frontend build wants the client in a source directory.

## See Also

- [Client runtime](../../client/index.md)
- [`build`](./build.md)
