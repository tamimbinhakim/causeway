# @causewayjs/next

Next.js helpers for the Causeway route-key client.

```bash
pnpm add @causewayjs/next @causewayjs/client
```

```tsx
"use client";

import { createHydrateClient } from "@causewayjs/next/client";
import { createClient } from "./client";

export const HydrateClient = createHydrateClient(createClient, {
  baseUrl: "/api",
});
```

```tsx
import { createServerHydration } from "@causewayjs/next";
import { headers } from "next/headers";
import { HydrateClient } from "./causeway-client";
import { createClient } from "./client";

const causeway = createServerHydration(createClient, {
  baseUrl: process.env.CAUSEWAY_API_URL,
  headers: await headers(),
  HydrateClient,
});

await causeway.prefetch("GET /customers/$id", { id });

return (
  <causeway.HydrateClient>
    <CustomerPage id={id} />
  </causeway.HydrateClient>
);
```

The helpers keep request headers request-scoped, provide small hydration wrappers, and expose idempotency header defaults for mutation calls.

The default shape mirrors the React Query hydration flow: prefetch into a server client, then render a hydration boundary without passing cache state through every page. Lower-level helpers are still available: `createServerClient(createClient, ...)`, `prefetch`, `prefetchMany`, `dehydrate`, `hydrate`, and `queryOptions`.

Use this package on the server side of a Next app. The generated client and `@causewayjs/react` still own the browser-side hooks.

## Docs

See the full Next.js guide in the Causeway docs: <https://github.com/tamimbinhakim/causeway/blob/main/docs/client/next.md>.

## License

MIT
