# `causeway build`

Emit the deployable artifact: IR snapshot, generated TS client, and a Python wheel.

```bash
causeway build
```

## Synopsis

```
causeway build [--target <dir>]
```

## Options

| Option            | Default | Description       |
| ----------------- | ------- | ----------------- |
| `--target` / `-o` | `dist/` | Output directory. |

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

1. Calls `causeway codegen` for the TS client.
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

- [Typed client](../../building/typed-client/index.md)
- [`diff`](./diff.md)
- [Deploying](../../deploying/index.md)
