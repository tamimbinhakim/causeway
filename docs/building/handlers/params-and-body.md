# Params and body

The handler signature is the API contract. Path params, query strings, request bodies, headers, and dependencies all bind by **annotation** — there are no `Path(...)` / `Query(...)` / `Body(...)` markers cluttering the signature.

## Path parameters

Path params come from the file path. The handler parameter name must match the bracketed segment:

```
src/app/routes/users/[id].py    →    /users/{id}
```

```python
from uuid import UUID
from causeway import get

@get
async def show(id: UUID) -> User: ...
```

The annotation drives parsing. `id: UUID` parses to `UUID`; `id: int` parses to `int`; a parse failure returns `400 bad_request` automatically.

See [Dynamic segments](../routing/dynamic-segments.md) for the full set of supported types.

## Query parameters

Any parameter that **isn't** a path segment, body, or `Annotated` dependency is treated as a query parameter:

```python
@get
async def list_users(limit: int = 50, offset: int = 0) -> list[User]: ...
```

URL: `GET /users?limit=20&offset=40`. Required (no default) query params return 400 if missing.

Optional with `| None`:

```python
@get
async def search(q: str | None = None) -> list[User]: ...
```

## Request body

A body comes in as a typed struct or dataclass. `msgspec.Struct` is recommended for performance; `pydantic.BaseModel` works too.

```python
from msgspec import Struct
from causeway import post


class NewUser(Struct):
    name: str
    email: str
    age: int | None = None


@post
async def create(data: NewUser) -> User: ...
```

JSON in, struct out. Validation errors return `400 bad_request` with a per-field error payload. The struct flows to the generated TS client as a typed argument.

> **Good to know.** Only one body parameter per handler — pick a single struct that captures everything the request sends.

## Headers

Pull a header off the request directly:

```python
from starlette.requests import Request
from causeway import get

@get
async def show(id: UUID, request: Request) -> User:
    api_version = request.headers.get("x-api-version", "v1")
    ...
```

For headers you read on every request (auth tokens, idempotency keys), promote them to a [scoped provider](../routing/scopes.md) so the handler stays clean.

## Raw bytes

For uploads or webhooks where you want the body as-is:

```python
from causeway import post, Bytes

@post
async def upload(body: Bytes) -> dict: ...
```

`Bytes` is a sentinel that tells `dyadpy` "give me the raw body, don't try to parse it."

## Dependencies (scoped providers)

A scoped DI provider binds via `Annotated[T, provider]`:

```python
from typing import Annotated
from app.lib.db import get_session

@get
async def list_users(
    db: Annotated[Session, get_session],
    limit: int = 50,
) -> list[User]: ...
```

The file router rewrites `Annotated[Session, get_session]` into `dyadpy.Depends(get_session)` at boot, so handler code stays declarative. See [Scopes](../routing/scopes.md).

> **Good to know.** Providers can take their own dependencies — Causeway hands the chain to `dyadpy.Depends`, which resolves it for you.

## The request context

For everything else (cookies, state, the raw ASGI scope), take a `dyadpy.Context` or a `starlette.requests.Request`:

```python
from dyadpy import Context

@get
async def show(id: UUID, ctx: Context) -> User:
    user_agent = ctx.request.headers.get("user-agent", "")
    ...
```

`Context` is dyadpy-native and gives you `ctx.set_status(...)`, `ctx.set_header(...)`, etc. `Request` is the Starlette object — use whichever feels more natural.

## Putting it together

```python
from typing import Annotated
from uuid import UUID
from msgspec import Struct
from causeway import patch, raises
from causeway.errors import NotFound

from app.lib.db import get_session


class UserPatch(Struct):
    name: str | None = None
    email: str | None = None


@patch
@raises(NotFound)
async def update(
    id: UUID,                                    # path param
    data: UserPatch,                             # body
    db: Annotated[Session, get_session],         # DI
    notify: bool = False,                        # query string
) -> User:
    user = await db.get(User, id)
    if user is None:
        raise NotFound(f"user {id}")
    update_user(user, data)
    if notify:
        await send_notification(user)
    return user
```

`PATCH /users/{id}?notify=true` with a JSON body — fully typed end-to-end.

## Next

- [Responses](./responses.md)
- [Errors](./errors.md)
- [Streaming](./streaming.md)
