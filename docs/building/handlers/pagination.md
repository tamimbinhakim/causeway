# Pagination

Causeway commits to one pagination shape: a `Paginated[T]` struct containing `items` and a `next_cursor` string. Cursors are opaque to clients — the framework only guarantees the cursor returned from request N decodes back into the payload you encoded for request N+1.

## The shape

```python
from msgspec import Struct
from causeway import Cursor, Paginated, get

class User(Struct):
    id: str
    name: str

@get
async def list_users(
    cursor: str | None = None,
    limit: int = 50,
) -> Paginated[User]:
    after = Cursor.decode(cursor).get("id")
    rows = await db.users.list(after=after, limit=limit + 1)
    more = len(rows) > limit
    items = rows[:limit]
    next_cursor = Cursor.encode({"id": items[-1].id}) if more else None
    return Paginated(items=items, next_cursor=next_cursor)
```

On the wire and in the generated TS client:

```ts
type Paginated_User_ = { items: User[]; next_cursor: string | null };
```

## Why cursor, not offset

Offset pagination skips rows under concurrent inserts and goes O(n) on deep pages — the canonical mistake every team makes once. Cursors index into a stable ordering column (usually the primary key or a `(created_at, id)` tuple) and stay correct under writes.

The framework deliberately does not provide an offset helper. If you need one, do it by hand.

## Encoding payloads

`Cursor.encode(payload)` turns a dict into a URL-safe base64 token. `Cursor.decode(token)` reverses it. Pass anything JSON-serializable:

```python
Cursor.encode({"id": last_row.id, "ts": last_row.created_at.isoformat()})
```

`Cursor.decode(None)` and `Cursor.decode("")` both return `{}` — the empty cursor means "first page." A malformed cursor raises `BadRequest` (400), not 500.

## End-of-pages

`next_cursor=None` is the explicit "no more pages" signal. Don't conflate it with an empty `items` list: a filter that returns nothing on page 1 is `Paginated(items=[], next_cursor=None)`.

## On the client

```ts
let cursor: string | undefined;
do {
  const page = await api.listUsers({ cursor, limit: 50 });
  for (const u of page.items) render(u);
  cursor = page.nextCursor ?? undefined;
} while (cursor);
```
