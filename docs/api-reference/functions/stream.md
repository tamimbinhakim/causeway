# `stream`

Marker for SSE return types. A handler that returns `stream[T]` is wired as an async iterator on the wire (`Content-Type: text/event-stream`) and as `AsyncIterable<T>` on the client.

```python
from causeway import get, stream
from msgspec import Struct


class Event(Struct):
    kind: str
    data: dict


@get
async def watch(thread_id: str) -> stream[Event]:
    async for evt in subscribe(thread_id):
        yield Event(kind=evt.kind, data=evt.data)
```

## Signature

```python
stream[T]    # type alias / marker
```

Re-exported from `dyadpy`. The handler **must** be an async generator (`yield` inside an `async def`) whose return annotation is `stream[T]`.

## Wire shape

```
event: message
data: {"kind":"chat.delta","data":{"text":"hi"}}

event: message
data: {"kind":"chat.delta","data":{"text":" there"}}
```

Each yielded value is JSON-serialized and sent as a single SSE `message` event.

## Client shape

```ts
const stream = await client.watch({ thread_id: "abc" });
for await (const event of stream) {
  console.log(event.kind, event.data);
}
```

## See also

- [Streaming](../../building/handlers/streaming.md)
