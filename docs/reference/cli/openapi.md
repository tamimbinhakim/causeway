# `causeway openapi`

Emit an OpenAPI 3.1 document from the same IR used by the route-key client.

```bash
causeway openapi app:app --out openapi.json
```

## Synopsis

```
causeway openapi [module] [--out <file>] [--title <title>] [--api-version <version>]
```

## Options

| Option          | Default        | Description               |
| --------------- | -------------- | ------------------------- |
| `--out` / `-o`  | `openapi.json` | Output JSON path.         |
| `--title`       | `Causeway API` | OpenAPI document title.   |
| `--api-version` | `0.0.0`        | OpenAPI document version. |

OpenAPI is an export surface for non-Causeway consumers. The primary TypeScript client remains the generated route-key client.

## See Also

- [Client runtime](../../client/index.md)
- [`ir`](./ir.md)
