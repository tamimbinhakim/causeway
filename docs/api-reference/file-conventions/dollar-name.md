# `$name`

Dot-flat dynamic segment. The `$`-prefixed piece becomes a path parameter; the handler signature drives parsing.

```
src/app/routes/users.$id.py            →    /users/{id}
src/app/routes/posts.$slug.py          →    /posts/{slug}
src/app/routes/api/v1.$version.posts.py →   /api/v1/{version}/posts
src/app/routes/users.$id.index.py      →    /users/{id}
```

## Rules

- The handler parameter name must match the `$`-prefixed piece (without the `$`). `users.$userId.py` requires `userId` in the signature.
- The annotation drives parsing.
- A trailing `.index` is dropped (means "match parent exactly").

## When to use vs `[name]`

- **Folders (`[name]`)** read better for deep, group-heavy trees and when you want to nest more routes under the parameter.
- **Dot-flat (`$name`)** reads better for shallow, parameter-light leaves where you don't need a folder. `users.$id.posts.py` is one line; `users/[id]/posts.py` is three directory hops.

You can mix them: `api/v1.$version.posts.py` uses both styles in the same path.

## Catch-all (reserved)

`$$rest` is reserved for v0.2+.

## See also

- [Dynamic segments](../../building/routing/dynamic-segments.md)
- [`[name].py`](./bracket-name.md) — folder equivalent.
