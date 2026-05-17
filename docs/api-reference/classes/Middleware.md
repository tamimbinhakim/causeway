# `Middleware`

Protocol for class-based middleware. Subclass and implement `async __call__(req, call_next)`.

```python
from causeway import Middleware
from causeway.middleware import Request, Response

class RequestId(Middleware):
    async def __call__(self, req: Request, call_next):
        rid = req.headers.get("x-request-id") or new_id()
        req.state.request_id = rid
        resp: Response = await call_next(req)
        resp.headers["x-request-id"] = rid
        return resp
```

## Protocol shape

```python
class Middleware(Protocol):
    async def __call__(self, req: Request, call_next: CallNext) -> Response: ...
```

Where:
- `Request` is `starlette.requests.Request`.
- `Response` is `starlette.responses.Response`.
- `CallNext = Callable[[Request], Awaitable[Response]]`.

## Installing

Inside a `_middleware.py`:

```python
middleware = [RequestId(), Timing()]
```

The discovery walker collects every `_middleware.py` it encounters and composes them by depth.

## Composition

For a request to `/users/{id}`:

```
app-level middleware →
  routes/_middleware.py →
    routes/users/_middleware.py →
      handler
```

Response unwinds in reverse: leaf middleware exits first, root last.

## When to use vs `@guard`

| Use `Middleware` when…                       | Use `@guard` when…                              |
| -------------------------------------------- | ----------------------------------------------- |
| You need to mutate the response              | You only need to assert before the handler      |
| You need to time, log, retry, or transform   | You only need to short-circuit on bad requests  |
| You need state shared across requests        | You're checking auth, headers, presence         |

## See also

- [Middleware](../../building/routing/middleware.md)
- [`@guard`](../decorators/guard.md)
- [`RequestIdMiddleware`](./RequestIdMiddleware.md)
