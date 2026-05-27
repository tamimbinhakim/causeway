# Dynamic segments

Dynamic segments capture part of the URL and pass it to the handler as a typed argument.

## Dynamic segment: `$name`

```
src/app/routes/users/$id.py     →    /users/{id}
src/app/routes/users.$id.py     →    /users/{id}
```

```python
from uuid import UUID
from causeway import get

@get
async def show(id: UUID) -> User: ...
```

The name after `$` must match the handler parameter exactly: `$id` requires `id`, `$userId` requires `userId`.

## Multiple segments

```
src/app/routes/users/$userId/posts/$postId.py    →    /users/{userId}/posts/{postId}
src/app/routes/users.$userId.posts.$postId.py    →    /users/{userId}/posts/{postId}
```

```python
@get
async def show(userId: UUID, postId: UUID) -> Post: ...
```

## Typed binding

The segment is just a string on the wire. The handler annotation drives parsing — `id: UUID` parses to a `UUID`, `id: int` parses to `int`, and a parse failure returns a `400 bad_request` automatically. The type also flows to the TypeScript client, so the caller can't pass a number where a UUID is expected.

| Annotation              | Wire shape        | Parse failure   |
| ----------------------- | ----------------- | --------------- |
| `id: int`               | digits only       | 400 bad_request |
| `id: UUID`              | RFC 4122 string   | 400 bad_request |
| `id: str`               | anything URL-safe | never fails     |
| `id: Literal["a", "b"]` | exact match       | 400 bad_request |

> **Good to know.** This is `causeway._runtime` doing the work — the file router only stamps the URL pattern. Any type the runtime knows how to parse via `msgspec.convert` is fair game.

## Dynamic folders

A `$` folder name binds the same way:

```
src/app/routes/users/$id/posts.py    →    /users/{id}/posts
src/app/routes/users/$id/index.py    →    /users/{id}
```

Handlers under that folder all see the parameter:

```python
# users/$id/posts.py
@get
async def list_posts(id: UUID) -> list[Post]: ...
```

## Literal siblings beat dynamic ones

When a folder contains both `$id.py` and a literal sibling (e.g. `risk-overrides/index.py`), the literal route always wins for matching requests:

```
routes/customers/$id.py                    →  /customers/{id}
routes/customers/risk-overrides/index.py   →  /customers/risk-overrides
```

`GET /customers/risk-overrides` hits the literal handler; `GET /customers/abc-123` falls through to `$id`. Discovery sorts routes by specificity (literal segments outrank parametric ones at every depth) before registration, so filesystem walk order doesn't shadow literal siblings.

## Catch-all (reserved)

`$$rest.py` and `$$rest/` are reserved for v0.2+. Today they raise `NotImplementedError` at boot. Track [the roadmap](../../../ROADMAP.md) for status.

## Common pitfalls

**Param name doesn't match the segment.**
`$id.py` with `async def show(user_id: UUID)` raises at boot with a clear error. The name has to match exactly, including case.

**Two routes resolve to the same URL.**
`users/index.py` and `users.py` both resolve to `/users`. The discovery walk raises a method-conflict error at boot listing both source files.

**Using bracket params.**
Bracket params are intentionally unsupported. Use `$id.py`, `$id/`, or dotted leaves like `users.$id.posts.py`.

## Next

- [Route groups](./route-groups.md)
- [Middleware](./middleware.md)
- [Reference — file conventions](../../api-reference/file-conventions/index.md)
