# `RequestIdMiddleware`

ASGI middleware that stamps every request with a stable id.

## Behavior

- Reads `X-Request-Id` from the incoming request, or generates a new UUID hex.
- Sets `request.state.request_id` so handlers can read it.
- Binds the id as a `structlog` contextvar so every log line in the request carries it.
- Adds `X-Request-Id` to the response on the way out.

## Installed by default

`create_app(..., request_id=True)` installs it at the app boundary. To opt out, pass `request_id=False`.

For manual setup:

```python
from starlette.middleware import Middleware as StarletteMiddleware
from causeway import RequestIdMiddleware

middleware = [StarletteMiddleware(RequestIdMiddleware)]
```

## Class shape

```python
class RequestIdMiddleware:
    HEADER = "x-request-id"

    def __init__(self, app: ASGIApp) -> None: ...
    async def __call__(self, scope, receive, send) -> None: ...
```

## Helper

```python
from causeway.observability import request_id_of

request_id_of(request)   # str | None
```

## See also

- [Observability](../../app/observability.md)
- [`configure_logging`](../functions/configure-logging.md)
