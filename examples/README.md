# Examples

Runnable starter projects exercising the v0.1 surface. Each example is self-contained and is **not** part of the publish pipeline — they exist to demo features and catch regressions.

| Example                 | Demonstrates                                                                        |
| ----------------------- | ----------------------------------------------------------------------------------- |
| [`minimal/`](./minimal) | The smallest possible Quay app: one handler, no plugins. Sanity check the dev loop. |

## Running an example

```bash
cd examples/minimal
uv sync
uv run quay dev
```

The dev server boots on `http://127.0.0.1:8000`. Visit `/__quay` for the diagnostics page.
