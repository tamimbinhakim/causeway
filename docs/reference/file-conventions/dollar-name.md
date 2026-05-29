# `$name`

Dynamic segment. The `$`-prefixed piece becomes a path parameter; the handler signature drives parsing. The HTTP path uses `{name}` and the public route key keeps `$name`.

```
src/app/routes/users/$id.py             →    /users/{id}
src/app/routes/users/$id/posts.py       →    /users/{id}/posts
```

```text
GET /users/$id
GET /users/$id/posts
```

## Rules

- The handler parameter name must match the `$`-prefixed piece (without the `$`). `users/$userId.py` requires `userId` in the signature.
- The annotation drives parsing.
- A trailing `/index.py` is dropped (means "match parent exactly").

## Catch-all (reserved)

`$$rest` is reserved for v0.2+.

## See also

- [Dynamic segments](../../backend/dynamic-segments.md)
