# `index.py`

Resolves to the URL of its parent folder.

```
src/app/routes/index.py            →    /
src/app/routes/users/index.py      →    /users
src/app/routes/users/$id/index.py      →    /users/{id}
```

## When to use it

- For collection endpoints under a parent named folder (`users/index.py` for `/users`).
- When the parent folder represents a feature (`billing/index.py`).

## When **not** to use it

- For a single-route feature where the folder adds no organization. Prefer `users.py` instead of `users/index.py`.

## Conflict

`users/index.py` and `users.py` both resolve to `/users`. If both exist with the same method, discovery raises at boot.

## See also

- [Defining routes](../../backend/routing.md)
- [File conventions](./index.md)
