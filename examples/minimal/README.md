# Example: minimal

The smallest possible Quay app. One handler, zero plugins. The point is to sanity-check the dev loop.

## What this will demonstrate

- `quay new` scaffolding shape.
- The file router picking up `src/app/routes/index.py` and `src/app/routes/health.py`.
- `quay dev` booting uvicorn + watcher + TypeScript client codegen + `/__quay` diagnostics page.

## Status

Structural placeholder — implementation lands with v0.1. See [`ROADMAP.md`](../../ROADMAP.md).

## Will run as

```bash
uv sync
uv run quay dev
```
