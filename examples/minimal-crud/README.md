# minimal-crud

A 30-line Quay app: file-based routing, scoped DI, typed errors, in-memory
storage. Run it:

```bash
cd examples/minimal-crud
uv sync
uv run uvicorn app:app --reload
```

Then:

```bash
curl http://127.0.0.1:8000/users/u1
curl -X POST http://127.0.0.1:8000/users -d '{"name":"ada"}' -H 'content-type: application/json'
```
