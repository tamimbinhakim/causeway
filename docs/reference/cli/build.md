# `causeway build`

Emit the deployable artifact: IR snapshot, generated TS client, and a Python wheel.

```bash
causeway build
```

## Synopsis

```
causeway build [--target <dir>] [--module <module:attr>] [--binary] [--sign] [--sbom] [--dry-run]
```

## Options

| Option            | Default   | Description                                                |
| ----------------- | --------- | ---------------------------------------------------------- |
| `--target` / `-o` | `dist/`   | Output directory.                                          |
| `--module` / `-m` | `app:app` | ASGI app import path to inspect for codegen.               |
| `--binary`        | `false`   | Build a self-contained AOT binary instead of a wheel.      |
| `--sign`          | `false`   | Sign the binary with `cosign sign-blob` (`--binary` only). |
| `--sbom`          | `false`   | Emit a CycloneDX SBOM via `syft` (`--binary` only).        |
| `--dry-run`       | `false`   | Freeze and plan the binary build, but skip compilation.    |

## Outputs

```
dist/
├── ir.json                          # IR snapshot
├── client/                          # Generated TypeScript client directory
│   ├── index.ts
│   ├── types.d.ts
│   ├── meta.ts
│   └── routes/
└── my_app-0.0.1-py3-none-any.whl    # Python wheel
```

## Pipeline

1. Calls [`causeway codegen`](./codegen.md) for the TS client.
2. Calls `python -m build --wheel --outdir dist/` for the wheel.

Both run via subprocess so failures surface with the original tool's error message.

## CI integration

Build on PR, diff against main to flag breaking changes:

```yaml
- run: causeway build -o dist-pr
- run: git checkout main && causeway build -o dist-main
- run: causeway diff dist-main/ir.json dist-pr/ir.json
```

## See also

- [Client runtime](../../client/index.md)
- [App Graph](../../client/app-graph.md)
- [`inspect`](./inspect.md)
- [`diff`](./diff.md)
- [Deploying](../../deploy/index.md)
