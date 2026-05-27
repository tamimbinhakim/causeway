# HTTP methods

Method decorators turn a function into a handler. They're bare — no `("/path")` argument — because the file router already knows the path from the file location.

## The decorators

```python
from causeway import get, post, put, patch, delete

@get
async def show(id: UUID) -> User: ...

@post
async def create(data: NewUser) -> User: ...

@put
async def replace(id: UUID, data: User) -> User: ...

@patch
async def update(id: UUID, data: UserPatch) -> User: ...

@delete
async def remove(id: UUID) -> None: ...
```

A handler can be `async def` or plain `def`. Async is preferred — most real handlers do I/O.

## Multiple methods in one file

All handlers in the same file share the same URL path. The decorator binds the method; the file location binds the path.

```python
# src/app/routes/users/$id.py
@get
async def show(id: UUID) -> User: ...

@patch
async def update(id: UUID, data: UserPatch) -> User: ...

@delete
async def remove(id: UUID) -> None: ...
```

That registers three routes on `/users/{id}`: `GET`, `PATCH`, `DELETE`.

> **Good to know.** The handler's function name doesn't matter for routing — only the decorator does. Use whatever name makes the file readable.

## Rules

1. **One method per function.** Decorating with both `@get` and `@post` raises `TypeError` at import.
2. **No method conflicts in a file.** Two `@get` handlers in the same file raise at boot — pick one or split into separate files.
3. **No path conflicts across files.** Two `@get` handlers that resolve to the same URL pattern (e.g. `users.py` and `users/index.py`) raise at boot.

All three are boot-time errors, not request-time — by the time you can hit the server, the route table is sound.

## What about OPTIONS, HEAD, TRACE?

Causeway doesn't ship `@options` / `@head` decorators. `OPTIONS` is handled by CORS middleware; `HEAD` is automatically derived from `GET` (Starlette default). If you need a custom method, drop down to `causeway.App.add_route` from your `plugins.py`.

## Status codes

Successful responses default to `200`. To return `201 Created` from a `POST` (the common case), return the resource — Causeway emits 201 automatically when the function name is `create` and the method is `POST`. For explicit control, raise `causeway.errors.*` or set `ctx.set_status(...)` from a `causeway.Context` parameter.

## Next

- [Params and body](./params-and-body.md)
- [Responses](./responses.md)
- [Errors](./errors.md)
- [Streaming](./streaming.md)
- [Reference — decorators](../../api-reference/decorators/get.md)
