# Errors

Built-in `HttpError` subclasses in `causeway.errors`. Declare them with
`@raises(...)` and raise them from a handler to return a typed error envelope
on the wire. The route-key client unwraps declared envelopes into
`CausewayError`. Undeclared errors that reach the global renderer use
`application/problem+json`.

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
    def to_dict(self, *, request=None, error_formatter=None) -> dict: ...
```

- `status` — HTTP status code.
- `code` — stable wire identifier (snake_case). **Don't change after shipping.**
- `message` — human-readable. Surfaced as `error.message` in typed envelopes and `detail` in problem+json fallback responses.
- `detail` — machine-readable dict. Surfaced as `error.detail` in typed envelopes and `params` in problem+json fallback responses.

## Subclassing

```python
from causeway.errors import HttpError

class QuotaExceeded(HttpError):
    status = 402
    code = "quota_exceeded"
```

Declare on the handler with `@raises(QuotaExceeded)` to flow it into the typed client.

## Wire shape

Declared route error:

```json
HTTP/1.1 404 Not Found
content-type: application/json

{
  "ok": false,
  "error": {
    "kind": "NotFound",
    "status": 404,
    "code": "not_found",
    "message": "user 00000000-...",
    "detail": {},
    "request_id": "abc123"
  }
}
```

Unhandled fallback error:

```json
HTTP/1.1 500 Internal Server Error
content-type: application/problem+json

{
  "type": "about:blank#internal",
  "title": "internal",
  "status": 500,
  "detail": "internal server error",
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

Built-in `HttpError` values suppress parser/decoder exception chains, so
expected 4xx failures stay short in tests and tools. Unexpected internal errors
keep their normal server traceback.

## Formatting `HttpError`

```python
from causeway.errors import HttpError, HttpErrorFormatter, format_http_error
```

`HttpErrorFormatter` is a callable:

```python
def formatter(error: HttpError, request: Request | None) -> dict: ...
```

Use `create_app(..., error_formatter=formatter)` to apply it to both declared
typed error envelopes and problem+json fallback responses. The formatter can
return any subset of `status`, `code`, `message`, and `detail`; missing fields
are filled from the original error.

## `render_problem`

```python
from causeway.errors import render_problem

resp = render_problem(exc, request_id="abc", error_formatter=formatter)
```

Used internally by the framework — useful in custom middleware if you need to render errors yourself.

## See also

- [Errors](../../backend/errors.md)
- [`@raises`](../decorators/raises.md)
- [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457)
