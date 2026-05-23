# Bracket Params

Bracket params are no longer a route convention. Use `$name` instead:

```
src/app/routes/users/$id.py        →    /users/{id}
src/app/routes/users/$id/posts.py  →    /users/{id}/posts
src/app/routes/users.$id.posts.py  →    /users/{id}/posts
```

The handler parameter name must match the `$` segment exactly. `$id.py` requires `id` in the signature.

Bracket filenames such as `[id].py` now fail at boot with a clear error.
