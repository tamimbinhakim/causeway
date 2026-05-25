# Responses

The handler's return annotation is the response shape on the wire **and** in the generated TypeScript client. One source of truth.

## Returning a struct

```python
from msgspec import Struct
from causeway import get

class User(Struct):
    id: UUID
    name: str
    email: str

@get
async def show(id: UUID) -> User:
    return User(id=id, name="ada", email="ada@example.com")
```

`User` becomes a `User` interface on the client. The serializer is `msgspec` for Structs, `pydantic` for `BaseModel`, `dataclasses.asdict` for `@dataclass` — whichever the return type uses.

## Returning a list

```python
@get
async def list_users() -> list[User]:
    return [User(...), User(...)]
```

`list[User]` becomes `User[]` on the client.

## No content

```python
@delete
async def remove(id: UUID) -> None:
    await db.delete(User, id)
```

Returns `204 No Content` and the client function returns `void`.

## Status codes

Defaults:

- `GET`, `PUT`, `PATCH` → `200 OK`
- `POST` → `201 Created` when the function name is `create`; `200 OK` otherwise.
- `DELETE` with `-> None` → `204 No Content`.

For explicit control, take a `dyadpy.Context`:

```python
from dyadpy import Context

@post
async def reset(ctx: Context) -> None:
    ctx.set_status(202)
    await enqueue_reset()
```

For error statuses, raise a declared `HttpError` — see [Errors](./errors.md).

## Custom headers

```python
from dyadpy import Context

@get
async def show(id: UUID, ctx: Context) -> User:
    ctx.set_header("Cache-Control", "private, max-age=60")
    return await load(id)
```

## Content type

JSON is the default. For other content types (HTML, binary), return a Starlette `Response` directly:

```python
from starlette.responses import HTMLResponse

@get
async def widget() -> HTMLResponse:
    return HTMLResponse("<div>hi</div>")
```

> **Good to know.** Returning a raw `Response` opts the route out of TS codegen — the return type is `Response`, not a typed value. Use this only when you need it (file downloads, HTML islands).

## Discriminated unions

A handler that returns one of several types narrows on the client side:

```python
from typing import Annotated, Literal
from msgspec import Struct

class Ok(Struct):
    kind: Literal["ok"] = "ok"
    value: int

class Pending(Struct):
    kind: Literal["pending"] = "pending"
    job_id: str

@get
async def status(id: UUID) -> Ok | Pending: ...
```

The client gets a discriminated union; `result.kind === "ok"` narrows to `Ok`.

## Envelope-style responses

Causeway doesn't impose an envelope (no automatic `{ ok, data, error }` wrap). If you want one, declare it explicitly:

```python
from typing import Generic, TypeVar
from msgspec import Struct

T = TypeVar("T")

class Envelope(Struct, Generic[T]):
    ok: bool
    data: T | None = None
    error: str | None = None

@get
async def show(id: UUID) -> Envelope[User]: ...
```

The generic flows to TypeScript faithfully.

## Errors as part of the contract

A typed error becomes part of the response shape via `@raises`:

```python
from causeway import get, raises
from causeway.errors import NotFound

@get
@raises(NotFound)
async def show(id: UUID) -> User: ...
```

The client sees `Result<User, NotFound>` and is forced to handle both branches. Full details in [Errors](./errors.md).

## Streaming responses

For SSE / async iterables, use `stream[T]`:

```python
from causeway import get, stream

@get
async def watch(thread_id: str) -> stream[Event]: ...
```

See [Streaming](./streaming.md).

## Next

- [Errors](./errors.md)
- [Streaming](./streaming.md)
- [Typed client](../typed-client/index.md)
