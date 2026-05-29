# React

`@causewayjs/react` is the React adapter over the owned route-key client. It keeps the surface small: one provider, one query hook, one mutation hook.

```bash
pnpm add @causewayjs/react @causewayjs/client
```

## Setup

Use the generated client from `causeway codegen` or `causeway build`:

```tsx
import { CausewayProvider } from "@causewayjs/react";
import { createClient } from "./generated/causeway/client";

const client = createClient({ baseUrl: "/api" });

export function Providers({ children }: { children: React.ReactNode }) {
  return <CausewayProvider client={client}>{children}</CausewayProvider>;
}
```

The provider accepts any Causeway route-key client. Generated clients carry route metadata, lazy route loading, and route-key input/output types.

Importing the generated client registers your app's route contracts with `@causewayjs/client`. After that, `useQuery("GET /customers/$id", ...)` infers the input, data, and error types from the route key. You should not write `useQuery<Customer>(...)` in normal app code.

## Queries

```tsx
import { useQuery } from "@causewayjs/react";

export function Customer({ id }: { id: string }) {
  const customer = useQuery("GET /customers/$id", { id });

  if (customer.pending) return <Skeleton />;
  if (customer.error) return <ErrorState error={customer.error} />;

  return <h1>{customer.data?.name}</h1>;
}
```

`queryOptions(...)` is also available when you want an options object that can be shared with a server prefetch call:

```tsx
import { queryOptions } from "@causewayjs/react";

const customerQuery = queryOptions("GET /customers/$id", { id });
const customer = useQuery(customerQuery);
```

`useQuery(routeKey, input, options)` returns:

- `data`
- `pending`
- `error`
- `refresh()`
- `setData(next)`

`enabled: false` keeps the hook idle until you call `refresh()` yourself.

```tsx
const customer = useQuery(
  "GET /customers/$id",
  { id },
  { enabled: Boolean(id) },
);
```

Inline input objects are safe. The runtime builds a canonical query key from route key, input, and scope, so React Compiler-era code does not need `useMemo` just to keep a query from looping.

## Mutations

```tsx
import { useMutation } from "@causewayjs/react";

const screen = useMutation("POST /customers/$id/screen", {
  feedback: {
    loading: "Screening customer...",
    success: "Customer screened",
    error: (error) => error.message,
  },
});

await screen({ id });
```

`useMutation(routeKey, options)` returns a callable function with:

- `pending`
- `error`
- `data`
- `reset()`

After a successful mutation, the client runtime runs the backend-declared `refreshes`. Failed mutations do not refresh.

## Feedback

Causeway does not pick a toast library. The provider receives a tiny feedback adapter:

```tsx
<CausewayProvider
  client={client}
  feedback={{
    loading: (message, id) => toast.loading(message, { id }),
    success: (message, id) => toast.success(message, { id }),
    error: (message, id) => toast.error(message, { id }),
  }}
>
  {children}
</CausewayProvider>
```

Mutation hooks emit feedback messages; the app decides whether those become toasts, banners, logs, or nothing.

## Errors

Declared backend errors throw `CausewayError`:

```tsx
import { CausewayError } from "@causewayjs/client";

try {
  await screen({ id });
} catch (error) {
  if (error instanceof CausewayError && error.kind === "Forbidden") {
    // show a permission message
  }
}
```

## See Also

- [Client runtime](./index.md)
- [Next.js](./next.md)
- [`@causewayjs/react` README](../../packages/causeway-react/README.md)
