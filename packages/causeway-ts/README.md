# @causewayjs/ts

Low-level TypeScript transport primitives used by Causeway-generated clients.

```bash
pnpm add @causewayjs/ts
```

Most apps should install `@causewayjs/client` and use the generated
`createClient()` helper. This package is the small shared transport layer:
request building, snake/camel conversion, SSE parsing, forwarded headers, typed
Causeway errors, and the route descriptor types consumed by generated route
chunks.

## Exports

| Export                      | What it does                                                                    |
| --------------------------- | ------------------------------------------------------------------------------- |
| `createRouteKeyClient(...)` | Builds the owned route-key runtime used by `@causewayjs/client`.                |
| `forwardHeaders(request)`   | Copies cookies, auth, locale, and tracing headers into server-side calls.       |
| `parseSSE(stream)`          | Parses `ReadableStream<Uint8Array>` into SSE frames.                            |
| `CausewayError`             | Error subclass for typed `@raises` failures and plain HTTP failures.            |
| `unwrapResult(value)`       | Converts a `{ ok, data/error }` envelope into data or a thrown `CausewayError`. |
| `Ok<R>` / `Err<R>`          | Type helpers for extracting success and error branches from `Result`.           |

## License

MIT
