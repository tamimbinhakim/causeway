# `configure_logging`

Set up structured logging via `structlog`.

```python
from causeway import configure_logging

configure_logging(level="INFO", json=True)
```

## Signature

```python
configure_logging(*, level: str = "INFO", json: bool = True) -> None
```

## Parameters

| Parameter | Default   | Notes                                                                            |
| --------- | --------- | -------------------------------------------------------------------------------- |
| `level`   | `"INFO"`  | Log level. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.              |
| `json`    | `True`    | `True` → JSON renderer (production). `False` → console renderer (local dev).    |

## What it sets up

Every log line gets:

- the timestamp (ISO 8601, UTC),
- the log level,
- the request id (if inside a request — bound by `RequestIdMiddleware`),
- any keyword fields you pass.

```python
import structlog
log = structlog.get_logger()

log.info("loading user", user_id="abc")
# {"timestamp":"...","level":"info","event":"loading user","user_id":"abc","request_id":"..."}
```

## Where to call it

In `src/app/lifespan.py` (or anywhere before the app starts handling requests). Calling it more than once is safe but pointless — the last call wins.

## Custom processors

`configure_logging` is the simple path. For custom processors (PII scrubbing, log sampling, alternate renderers), call `structlog.configure(...)` yourself after `configure_logging` returns.

## See also

- [Observability](../../building/observability/index.md)
- [`RequestIdMiddleware`](../classes/RequestIdMiddleware.md)
- [`configure_otel`](./configure-otel.md)
