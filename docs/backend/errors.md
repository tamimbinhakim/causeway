# Errors

Causeway uses two error mechanisms in tandem:

1. **Typed `HttpError` subclasses** for errors you declare with `@raises(...)`.
   On the wire these use the runtime's `{ ok: false, error }` envelope. The
   route-key client unwraps that envelope and throws a typed `CausewayError`.
2. **`application/problem+json`** ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457))
   for undeclared/unhandled exceptions that reach the global renderer.

## Built-in errors

```python
from causeway.errors import (
    BadRequest,      # 400 bad_request
    Unauthorized,    # 401 unauthorized
    Forbidden,       # 403 forbidden
    NotFound,        # 404 not_found
    Conflict,        # 409 conflict
    TooManyRequests, # 429 too_many_requests
    Internal,        # 500 internal
)
```

Each carries:

- a `status` int (HTTP status code),
- a stable `code` string (the wire identifier),
- an optional `message` (string),
- an optional `detail` dict for machine-readable fields.

## Raising an error

```python
from causeway import get, raises
from causeway.errors import NotFound

@get
@raises(NotFound)
async def show(id: UUID) -> User:
    user = await db.get(User, id)
    if user is None:
        raise NotFound(f"user {id}")
    return user
```

`@raises(NotFound)` declares the error as part of the contract. On the wire, the response becomes:

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

On the route-key client, a successful call returns `User`; the declared error branch becomes the route's `RouteError<K>` type and is thrown as `CausewayError`.

```ts
import { CausewayError } from "@causewayjs/client";

try {
  const user = await client.query("GET /users/$id", { id });
  console.log(user.name);
} catch (error) {
  if (error instanceof CausewayError && error.kind === "NotFound") {
    // typed route error
  }
}
```

## Multiple typed errors

Stack `@raises` for handlers that can fail in more than one named way:

```python
@post
@raises(BadRequest, Conflict)
async def create(data: NewUser) -> User:
    if not data.email:
        raise BadRequest("email required")
    if await email_exists(data.email):
        raise Conflict("email already in use")
    return create_user(data)
```

The client sees `RouteError<"POST /users">` as `BadRequest | Conflict`.

## Custom error types

Subclass `HttpError`:

```python
from causeway.errors import HttpError

class QuotaExceeded(HttpError):
    status = 402
    code = "quota_exceeded"
```

```python
@raises(QuotaExceeded)
async def upload(...) -> File:
    if await over_quota(user):
        raise QuotaExceeded(
            "monthly quota exceeded",
            detail={"used": 95, "limit": 100},
        )
    ...
```

The `code` field is the stable identifier — keep it kebab/snake-case and don't change it once you ship. The class name flows into the TS union as `QuotaExceeded`.

## Detail vs message

```python
raise BadRequest(
    "validation failed",
    detail={"field": "email", "reason": "format"},
)
```

- `message` → human-readable, surfaced as `error.message` in declared error envelopes and `detail` in problem+json fallback responses.
- `detail` (dict) → machine-readable, surfaced as `error.detail` in declared error envelopes and `params` in problem+json fallback responses.

The client can inspect both: `error.message` (string), `error.detail` (dict).

## App-level formatting

Causeway keeps error creation close to the handler, but lets the app translate
typed `HttpError` values into final wire messages at the boundary. Pass
`error_formatter=` to `create_app`:

```python
from starlette.requests import Request

from causeway import create_app
from causeway.errors import HttpError


def format_error(exc: HttpError, request: Request | None) -> dict:
    if exc.message == "invalid_phone":
        return {
            "message": "Phone number is not valid for the selected country",
            "detail": {**exc.detail, "reason": "invalid_phone"},
        }
    return {"message": exc.message}


app = create_app("app/routes", error_formatter=format_error)
```

The formatter is called for both declared `@raises(...)` error envelopes and
undeclared `HttpError` values rendered as problem+json. Any omitted `status`,
`code`, `message`, or `detail` field is filled from the original error.

## What about non-typed exceptions?

Anything that is not declared on the route with `@raises(...)` is not converted into a typed route error branch. If it reaches Causeway's global renderer, it becomes `application/problem+json`.

Unknown internal exceptions are rendered as `500 internal` with a generic message:

```json
{
  "type": "about:blank#internal",
  "title": "internal",
  "status": 500,
  "detail": "internal server error"
}
```

The original exception message is **never** surfaced — it might contain secrets, stack frames, or SQL. To opt into a custom response, subclass `HttpError`.

Two convenience exceptions get special treatment (so `@guard` functions can stay terse):

| Exception         | Rendered as     |
| ----------------- | --------------- |
| `PermissionError` | 403 `forbidden` |
| `LookupError`     | 404 `not_found` |

## Request id in errors

If the [`RequestIdMiddleware`](../app/observability.md) is installed (the default),
every typed error envelope carries `error.request_id`, and every problem+json
error carries top-level `request_id`. Pair it with structured logs and you can
grep one request across services.

## Traceback shape

Public 4xx errors should be short. Causeway raises built-in `HttpError` values
without chaining parser/decoder exceptions into the traceback. Undeclared
internal exceptions still keep the full server-side traceback for debugging.

## Errors in guards

A `@guard` that raises produces the same response shape as a handler that raises:

```python
from causeway import guard

@guard
async def require_admin(req):
    user = await current_user(req)
    if not user:
        raise Unauthorized("login required")
    if not user.is_admin:
        raise Forbidden("admin only")
```

The error flows through the same renderer. To declare the guard's possible errors on the client side, list them on every handler the guard wraps via `@raises(Unauthorized, Forbidden)` — or accept that guard-level errors are best treated as "any route can return these" and document them separately.

## Why problem+json

It's a published standard (RFC 9457). It gives the client a stable `type` URI to dispatch on, a `status`, a `title`, and structured `params`. Clients written in any language can parse it without bespoke deserializers.

## Next

- [Reference — error types](../reference/classes/errors.md)
- [Reference — `@raises`](../reference/decorators/raises.md)
- [Observability](../app/observability.md) — request IDs in logs and traces.
