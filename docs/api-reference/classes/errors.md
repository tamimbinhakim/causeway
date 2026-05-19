# Errors

Built-in `HttpError` subclasses in `causeway.errors`. Raise them from a handler (or a guard) and the framework renders `application/problem+json`.

```python
from causeway.errors import (
    HttpError,       # base class
    BadRequest,      # 400 bad_request
    Unauthorized,    # 401 unauthorized
    Forbidden,       # 403 forbidden
    NotFound,        # 404 not_found
    Conflict,        # 409 conflict
    TooManyRequests, # 429 too_many_requests
    Internal,        # 500 internal
)
```

## `HttpError` (base)

```python
class HttpError(Exception):
    status: int = 500
    code: str = "internal"

    def __init__(self, message: str | None = None, *, detail: dict | None = None): ...
```

- `status` — HTTP status code.
- `code` — stable wire identifier (snake_case). **Don't change after shipping.**
- `message` — human-readable. Surfaced as `detail` in the rendered body.
- `detail` — dict. Surfaced as `params` in the rendered body.

## Subclassing

```python
from causeway.errors import HttpError

class QuotaExceeded(HttpError):
    status = 402
    code = "quota_exceeded"
```

Declare on the handler with `@raises(QuotaExceeded)` to flow it into the typed client.

## Wire shape

```json
HTTP/1.1 404 Not Found
content-type: application/problem+json

{
  "type": "about:blank#not_found",
  "title": "not_found",
  "status": 404,
  "detail": "user 00000000-...",
  "params": {},
  "request_id": "abc123"
}
```

## Special exceptions

The renderer also handles two non-HttpError exceptions for convenience:

| Raised            | Rendered status                   |
| ----------------- | --------------------------------- |
| `PermissionError` | 403 `forbidden`                   |
| `LookupError`     | 404 `not_found`                   |
| anything else     | 500 `internal` (message scrubbed) |

## `render_problem`

```python
from causeway.errors import render_problem

resp = render_problem(exc, request_id="abc")
```

Used internally by the framework — useful in custom middleware if you need to render errors yourself.

## See also

- [Errors](../../building/handlers/errors.md)
- [`@raises`](../decorators/raises.md)
- [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)
