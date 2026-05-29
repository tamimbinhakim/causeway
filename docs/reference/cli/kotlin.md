# `causeway kotlin`

Generate a Kotlin client from the route IR.

```bash
causeway kotlin app:app --out Causeway.kt
```

## Synopsis

```
causeway kotlin [module] [--out <file>]
```

## Options

| Option         | Default       | Description         |
| -------------- | ------------- | ------------------- |
| `--out` / `-o` | `Causeway.kt` | Output Kotlin file. |

Kotlin generation is an auxiliary export. The canonical JavaScript/TypeScript surface is still the generated route-key client.

## See Also

- [`ir`](./ir.md)
- [IR stability](../../stability/ir-stability.md)
