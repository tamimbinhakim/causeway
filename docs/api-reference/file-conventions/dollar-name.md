# `$name`

Dynamic segment. The `$`-prefixed piece becomes a path parameter; the handler signature drives parsing.

```
src/app/routes/users/$id.py             →    /users/{id}
src/app/routes/users/$id/posts.py       →    /users/{id}/posts
src/app/routes/users.$id.py             →    /users/{id}
src/app/routes/api/v1.$version.posts.py →    /api/v1/{version}/posts
```

## Rules

- The handler parameter name must match the `$`-prefixed piece (without the `$`). `users.$userId.py` requires `userId` in the signature.
- The annotation drives parsing.
- A trailing `.index` or `/index.py` is dropped (means "match parent exactly").

## Folder vs dotted

- **Folders (`users/$id/posts.py`)** read better for deep, group-heavy trees and when you want to nest more routes under the parameter.
- **Dotted leaves (`users.$id.posts.py`)** read better for shallow, parameter-light leaves where you don't need a folder.

You can mix them: `api/v1.$version.posts.py` uses a folder prefix plus dotted dynamic leaf pieces.

## Catch-all (reserved)

`$$rest` is reserved for v0.2+.

## See also

- [Dynamic segments](../../building/routing/dynamic-segments.md)
