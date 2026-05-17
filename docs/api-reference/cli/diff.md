# `causeway diff`

Compare two IR snapshots and flag breaking changes. Delegates to `dyadpy diff`.

```bash
causeway diff dist-main/ir.json dist-pr/ir.json
```

## Synopsis

```
causeway diff <baseline> <candidate>
```

## Arguments

| Argument      | Description                                  |
| ------------- | -------------------------------------------- |
| `<baseline>`  | Path to the older IR snapshot.               |
| `<candidate>` | Path to the newer IR snapshot.               |

## What it reports

- Routes added / removed.
- Routes whose response type changed.
- Error contract changes (new branches, removed branches).
- Query / body schema changes.
- Settings exposed-to-client changes.

Each change is classified as **breaking** or **non-breaking** (see [IR stability](../../stability/ir-stability.md)).

## Exit codes

`0` on success (no breaking changes), non-zero on breaking changes. CI-friendly.

## CI integration

```yaml
- run: causeway build -o dist-pr
- run: git checkout main && causeway build -o dist-main
- run: causeway diff dist-main/ir.json dist-pr/ir.json
```

## See also

- [Typed client](../../building/typed-client/index.md)
- [IR stability](../../stability/ir-stability.md)
- [`build`](./build.md)
