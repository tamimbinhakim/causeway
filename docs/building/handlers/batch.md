# Batch endpoints

A batch endpoint accepts a list of items and returns per-item success/failure. HTTP 207 (`Multi-Status`) carries the mixed result; 200 means everything succeeded. The framework provides one shape — `BatchResult[T, E]` — so the TS client always knows what to expect.

## The shape

```python
from causeway import batch, post, raises, BatchResult, BatchFailure
from causeway.errors import BadRequest

@post
@batch
@raises(BadRequest)
async def create_many(items: list[NewUser]) -> BatchResult[User, BadRequest]:
    out: BatchResult[User, BadRequest] = BatchResult()
    for item in items:
        try:
            out.ok.append(await create_user(item))
        except BadRequest as e:
            out.failed.append(BatchFailure(input=item, error=e))
    return out
```

The `@batch` decorator sets status `207` when `out.failed` is non-empty, `200` otherwise. The decorator does not catch exceptions on your behalf — you control the per-item loop, which means you decide what counts as a per-item failure vs. a request-level failure.

## On the wire

```ts
type BatchResult_User__BadRequest_ = {
  ok: User[];
  failed: { input: NewUser; error: { kind: "BadRequest"; ... } }[];
};
```

The `error` discriminator (`kind`) matches the one used by `@raises` errors, so clients narrow with the same pattern in both places.

## Edge cases

- **All failed** → `207`, body has empty `ok` and populated `failed`. (Not `400` — the request itself was well-formed.)
- **All succeeded** → `200`.
- **Empty input** → `200` with both arrays empty. Don't 400.

## What `@batch` is not

It is not a transaction. Each iteration is independent — items in `ok` are persisted whether or not later items succeed. If you need all-or-nothing semantics, do the work in a `transaction()` block and 4xx the whole request on the first failure instead.
