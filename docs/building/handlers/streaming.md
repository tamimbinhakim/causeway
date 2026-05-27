# Streaming

Server-Sent Events (SSE) with a typed envelope on both ends. A handler returns `stream[T]`; the client receives `AsyncIterable<T>`.

## The basics

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

On the wire, this is `Content-Type: text/event-stream` with each event encoded as:

```
event: message
data: {"kind":"chat.delta","data":{"text":"hi"}}

```

On the client (TypeScript):

```ts
const stream = await client.watch({ thread_id: "abc" });
for await (const event of stream) {
  console.log(event.kind, event.data);
}
```

## When to use streaming vs. polling

- **Streaming** — when the producer pushes events on its own schedule (chat tokens, log tails, build progress, server-side state diffs).
- **Polling** — when the consumer drives the cadence (every 30s status check, dashboard refresh). Skip the SSE complexity.
- **Background tasks + result polling** — for long jobs the client kicks off and waits for. The `@task` decorator handles enqueue; a separate `GET /jobs/{id}` polls. See [Tasks](../tasks/index.md).

## Backpressure

The handler is an async generator — yielding too fast without consumer pickup buffers in memory. For high-throughput streams, gate the producer on consumer signals (e.g. acknowledge messages, sliding window).

## Disconnect handling

When the client disconnects, the next `yield` raises `asyncio.CancelledError`. Wrap cleanup in `try / finally`:

```python
@get
async def watch(thread_id: str) -> stream[Event]:
    sub = await subscribe(thread_id)
    try:
        async for evt in sub:
            yield Event(kind=evt.kind, data=evt.data)
    finally:
        await sub.aclose()
```

## Heartbeats

Long-lived SSE connections sometimes get killed by intermediaries (proxies, NAT). Send a periodic heartbeat:

```python
import asyncio

@get
async def watch(thread_id: str) -> stream[Event]:
    sub = await subscribe(thread_id)
    last = time.monotonic()
    async for evt in sub:
        yield Event(kind=evt.kind, data=evt.data)
        last = time.monotonic()
        if time.monotonic() - last > 15:
            yield Event(kind="heartbeat", data={})
```

For HTTP/2 + Cloudflare, 15-30s is a reasonable interval. Tune for your stack.

## What's in `stream[T]`

`stream[T]` is a marker that tells the runtime "this handler is an async generator of `T`." The IR records the element type; the codegen emits the right client type (`AsyncIterable<T>` in TypeScript with proper narrowing).

## Bidirectional streams

For full duplex, use WebSockets via Starlette's WebSocket route directly — Causeway doesn't wrap WebSockets into a typed primitive yet. Track [the roadmap](../../../ROADMAP.md) for a `dual_stream[Req, Resp]` proposal.

## Caveats

- SSE is HTTP/1.1 friendly but doesn't multiplex on HTTP/2 by default — some browsers cap concurrent connections per origin.
- Buffering proxies (some CDNs, some reverse-proxy defaults) can break SSE. Set `X-Accel-Buffering: no` for nginx, disable buffering at the LB.
- The handler return type **must** be `stream[T]` for codegen to recognize it. A bare `AsyncIterable[T]` won't emit the SSE client wrapper.

## Next

- [Tasks](../tasks/index.md) — for background work, not request-shaped streams.
- [Reference — `stream`](../../api-reference/functions/stream.md)
