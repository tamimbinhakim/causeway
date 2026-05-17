# Errors

Causeway uses two error mechanisms in tandem:

1. **Typed `HttpError` subclasses** that flow into the response body and the generated TypeScript client.
2. **`application/problem+json`** ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)) as the wire shape, automatically.

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
- an optional `detail` (dict, surfaced as `params` in the rendered body).

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
content-type: application/problem+json

{
  "type": "about:blank#not_found",
  "title": "not_found",
  "status": 404,
  "detail": "user 00000000-...",
  "request_id": "abc123"
}
```

On the client, the function signature is `Promise<Result<User, NotFound>>` — the caller has to handle both branches.

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

The client sees `Result<User, BadRequest | Conflict>`.

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

- `message` → human-readable, surfaced as `detail` in the problem+json body.
- `detail` (dict) → machine-readable, surfaced as `params` in the body.

The client can inspect both: `error.detail` (the message string), `error.params` (the dict).

## What about non-typed exceptions?

Anything that isn't an `HttpError` subclass is rendered as `500 internal` with a generic message:

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

| Exception           | Rendered as            |
| ------------------- | ---------------------- |
| `PermissionError`   | 403 `forbidden`        |
| `LookupError`       | 404 `not_found`        |

## Request id in errors

If the [`RequestIdMiddleware`](../observability/index.md) is installed (the default), every error response carries a `request_id` field. Pair it with structured logs and you can grep one request across services.

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

- [Reference — error types](../../api-reference/classes/errors.md)
- [Reference — `@raises`](../../api-reference/decorators/raises.md)
- [Observability](../observability/index.md) — request IDs in logs and traces.
