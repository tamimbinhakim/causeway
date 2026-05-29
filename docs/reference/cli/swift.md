# `causeway swift`

Generate a Swift client from the route IR.

```bash
causeway swift app:app --out Causeway.swift
```

## Synopsis

```
causeway swift [module] [--out <file>]
```

## Options

| Option         | Default          | Description        |
| -------------- | ---------------- | ------------------ |
| `--out` / `-o` | `Causeway.swift` | Output Swift file. |

Swift generation is an auxiliary export. The canonical JavaScript/TypeScript surface is still the generated route-key client.

## See Also

- [`ir`](./ir.md)
- [IR stability](../../stability/ir-stability.md)
