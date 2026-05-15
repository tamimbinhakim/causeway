# minimal

The smallest possible Causeway app. One handler, zero plugins, no DB. Use it
to sanity-check the dev loop on a fresh checkout.

## Layout

```
minimal/
├── pyproject.toml
├── causeway.toml
└── app/
    ├── __init__.py
    ├── app.py            # `app = create_app("app/routes")`
    └── routes/
        └── index.py      # GET /
```

## Run

```bash
cd examples/minimal
uv sync
uv run uvicorn app.app:app --reload
```

Then:

```bash
curl http://127.0.0.1:8000/
# → {"message":"hello from causeway"}

curl http://127.0.0.1:8000/healthz
# → {"status":"ok"}

curl http://127.0.0.1:8000/__causeway   # diagnostics page (HTML)
```

## What's wired

- `create_app("app/routes")` walks the routes tree, registers handlers,
  attaches `/healthz`, `/readyz`, `/__causeway`, and the request-id +
  problem+json error renderer.
- The file router discovers `app/routes/index.py` and registers `GET /`.
- The return type (`Hello`, a `msgspec.Struct`) is the wire schema — no
  separate request/response model.
