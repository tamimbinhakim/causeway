# `@raises`

Declare typed errors a handler may raise. Each declared error becomes a branch in the response's `Result<T, E>` union on the client.

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

Re-exported from `dyadpy`. The decorator stamps the handler with the declared error types so `dyadpy`'s codegen can emit them in the IR.

## Behavior

- Each error type must subclass `HttpError` (so it has a `status` and `code`).
- The actual exception still has to be raised in the handler body — `@raises` is **declarative**; it doesn't catch anything.
- A declared `HttpError` returns `{ ok: false, error: ... }` with the error's HTTP status.
- A handler that raises an undeclared `HttpError` can still be rendered by the global error renderer, but the TS client won't have a typed `Result` branch for it.

## Wire shape

A `@raises(NotFound)` declaration produces this on the client:

```ts
Result<User, NotFound>;
```

`NotFound` is a TypeScript interface mirroring the Python class — `{ kind: "NotFound", status: number, code: string, message: string, detail: Record<string, unknown>, requestId?: string | null }`.

## See also

- [Errors](../../building/handlers/errors.md)
- [`HttpError`](../classes/errors.md)
- [Typed client](../../building/typed-client/index.md)
