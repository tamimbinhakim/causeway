# Benchmarks

A reproducible harness comparing Quay vs FastAPI vs Litestar vs the underlying RPC layer (raw `dyadpy`) across:

- Cold start
- p50 / p95 / p99 request latency
- Throughput (req/s) at concurrency 1 / 16 / 64 / 256

## Status

Placeholder. Lands in v0.2 per [`ROADMAP.md`](../ROADMAP.md). Benchmarks gated on the v0.1 core being complete enough to host identical handlers across frameworks.

## Will run as

```bash
cd benchmarks
uv sync
uv run python bench.py --target quay
uv run python bench.py --target dyadpy
uv run python bench.py --target fastapi
uv run python bench.py --target litestar
uv run python bench.py --compare results/
```

## What's measured

A canonical handler implemented identically across all four targets: validate a request body, look up an item, return JSON. The point is to compare framework overhead, not application logic. Including raw `dyadpy` is the floor — it measures how much overhead Quay's project-shape layer (file router, scope graph, plugin registry) adds on top.

Vendor-blog numbers ("9x faster than X") are deliberately avoided — these benchmarks publish raw output and let readers draw conclusions.
