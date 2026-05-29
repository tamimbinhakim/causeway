# `@raises`

Declare typed errors a handler may raise. Each declared error becomes part of the route's generated `RouteError<K>` type.

```python
from causeway import get, raises
from causeway.errors import NotFound, BadRequest

@get
@raises(NotFound, BadRequest)
async def show(id: UUID) -> User: ...
```

## Signature

```python
raises(*errors: type[HttpError]) -> Callable[[Handler], Handler]
```

The decorator stamps the handler with the declared error types so the codegen can emit them in the IR.

## Behavior

- Each error type must subclass `HttpError` (so it has a `status` and `code`).
- The actual exception still has to be raised in the handler body — `@raises` is **declarative**; it doesn't catch anything.
- A declared `HttpError` returns `{ ok: false, error: ... }` on the wire with the error's HTTP status.
- The route-key client unwraps that envelope and throws `CausewayError`.
- A handler that raises an undeclared `HttpError` can still be rendered by the global error renderer, but the TS client won't have a typed `RouteError<K>` branch for it.

## Wire shape

A `@raises(NotFound)` declaration produces this on the client:

```ts
RouteError<"GET /users/$id">; // NotFound
```

`NotFound` is a TypeScript interface mirroring the Python class — `{ kind: "NotFound", status: number, code: string, message: string, detail: Record<string, unknown>, requestId?: string | null }`.

## See also

- [Errors](../../backend/errors.md)
- [`HttpError`](../classes/errors.md)
- [Client runtime](../../client/index.md)
