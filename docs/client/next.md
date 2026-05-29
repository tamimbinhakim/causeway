# Next.js

`@causewayjs/next` adds server-side helpers for the generated route-key client. It does not replace `@causewayjs/react`; use this package in server components, route handlers, and server actions where request headers need to be forwarded.

```bash
pnpm add @causewayjs/next @causewayjs/client
```

## The Default Shape

Create one client boundary for the browser. This is the app-owned place where the generated client is configured for client-side calls:

```tsx
"use client";

import { createHydrateClient } from "@causewayjs/next/client";
import { createClient } from "./generated/causeway/client";

export const HydrateClient = createHydrateClient(createClient, {
  baseUrl: "/api",
});
```

Then prefetch on the server and wrap the client tree:

```tsx
import { createServerHydration } from "@causewayjs/next";
import { headers } from "next/headers";
import { HydrateClient } from "./causeway-client";
import { createClient } from "./generated/causeway/client";

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const causeway = createServerHydration(createClient, {
    baseUrl: process.env.CAUSEWAY_API_URL!,
    headers: await headers(),
    HydrateClient,
  });

  await causeway.prefetch("GET /customers/$id", { id });

  return (
    <causeway.HydrateClient>
      <CustomerPage id={id} />
    </causeway.HydrateClient>
  );
}
```

That is the React Query-like flow: prefetch into a request-scoped server client, then render a hydration boundary. Normal pages do not pass cache state around manually. `"GET /customers/$id"` infers `{ id: string }` for input and the route's response type for cached data.

You can also render the boundary as a function when that reads better:

```tsx
return causeway.hydrate(<CustomerPage id={id} />);
```

## Client Hooks After Hydration

Inside the boundary, React hooks read from the hydrated cache before they fetch:

```tsx
"use client";

import { useQuery } from "@causewayjs/react";

export function CustomerPage({ id }: { id: string }) {
  const customer = useQuery("GET /customers/$id", { id });
  return <h1>{customer.data?.name}</h1>;
}
```

You can still hydrate manually when you are building lower-level infrastructure:

```ts
import { hydrate } from "@causewayjs/next";

const client = createClient({ baseUrl: "/api" });
hydrate(client, snapshot);
```

## Lower-Level Server Client

Use `createServerClient` when you need the server client object for additional calls:

```ts
import {
  createServerClient,
  dehydrate,
  prefetch,
  prefetchMany,
} from "@causewayjs/next";
import { headers } from "next/headers";
import { createClient } from "./generated/causeway/client";

const client = createServerClient(createClient, {
  baseUrl: process.env.CAUSEWAY_API_URL!,
  headers: await headers(),
});

const customer = await prefetch(client, "GET /customers/$id", { id });

await prefetchMany(client, ["GET /customers/$id", { id }], ["GET /customers"]);

const snapshot = dehydrate(client);
```

`createServerClient(createClient, ...)` hides generated metadata wiring. The older object form still works for low-level clients:

```ts
createServerClient({ baseUrl, headers, routeMeta, loadRoute });
```

`createServerClient` forwards request-scoped headers through `forwardHeaders`. That includes cookies and auth headers by default, so server-side prefetches act like the current user.

`queryOptions(...)` is available for teams that prefer an options object, but the standard Causeway route-key form is `prefetch(client, "GET /route/$id", input)` and `useQuery("GET /route/$id", input)`.

## Mutations and Idempotency

Use `idempotencyHeaders()` when a server action may be retried:

```ts
import { idempotencyHeaders } from "@causewayjs/next";

await client.mutate(
  "POST /customers/$id/screen",
  { id },
  {
    headers: idempotencyHeaders(),
  },
);
```

The server still owns idempotency behavior through `IdempotencyMiddleware`. The helper only supplies the standard header.

## See Also

- [React](./react.md)
- [Client runtime](./index.md)
- [`@causewayjs/next` README](../../packages/causeway-next/README.md)
