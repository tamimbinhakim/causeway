# causeway-ts

> The tiny TypeScript runtime imported by causeway-generated clients.

```bash
pnpm add causeway-ts
```

You shouldn't have to think about this package much. The
[`causeway`](https://pypi.org/project/causeway/) Python CLI writes a generated
`client/` directory into your frontend that imports from `causeway-ts`. That's it.

> **Why `causeway-ts` and not `causeway-react`?**
> Because this package is intentionally framework-agnostic. It's the
> tiny TypeScript runtime that the generated client imports
> regardless of where it ends up — Next.js, Vite + React, SvelteKit,
> SolidStart, Astro, plain HTML, a Node script. The name `causeway-ts`
> reflects the language (TypeScript), not a framework. Framework-specific
> bindings live in their own packages:
>
> | Package           | What it adds                                                          | Status                  |
> | ----------------- | --------------------------------------------------------------------- | ----------------------- |
> | `causeway-ts`     | The core TypeScript runtime. Required.                                | **v0.1 (this package)** |
> | `causeway-react`  | `useQuery`, `useSubscription`, `useMutation` hooks via TanStack Query | v0.1                    |
> | `causeway-svelte` | Svelte 5 store bindings                                               | v0.1                    |
> | `causeway-solid`  | SolidJS `createResource` / signal bindings                            | v0.1                    |
>
> If you only need React, you'll still install `causeway-ts` (the
> generated client imports it) _plus_ `causeway-react` for the hooks.

Hard rules I've held this package to:

- **Zero runtime dependencies.** Anything we need (SSE parsing, nested
  dispatch) ships inline.
- **Tree-shakable.** ESM-first, side-effect-free.
- **Tiny.** Target is under ~3 KB min+gz. We check it in CI.

## What's in it

| Export                                                                           | What it does                                                                                                            |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `createLazyClient<ApiRoutes>({ routeMeta, loadRoute, baseUrl, headers, fetch })` | Returns the nested object your generated `api.*` calls dispatch through while loading full route descriptors on demand. |
| `forwardHeaders(request)`                                                        | Copies cookies/auth/tracing headers into SSR calls.                                                                     |
| `parseSSE(stream)`                                                               | Streams a `ReadableStream<Uint8Array>` into typed SSE frames.                                                           |
| `unwrapResult(value)`                                                            | Unwrap a `Result<T, E>` envelope onto `data` / `throw error`. Used by the binding packages.                             |
| `Result<T, E>` (type)                                                            | `\{ ok: true; data: T \} \| \{ ok: false; error: E \}` — output of `@raises` routes.                                    |
| `Ok<R>` / `Err<R>` (types)                                                       | Extract success / error type from a route's `Return`.                                                                   |

If you find yourself reaching for something else, that's probably a bug
in the codegen — open an
[issue](https://github.com/tamimbinhakim/causeway/issues).

## License

MIT
