# Solid

`@causewayjs/solid` exposes Solid resources over the shared route-key client.

```bash
pnpm add @causewayjs/solid @causewayjs/client solid-js
```

## Setup

```ts
// src/lib/causeway.ts
import { createCausewayResources } from "@causewayjs/solid";
import { createClient } from "./generated/causeway/client";

export const client = createClient({ baseUrl: "/api" });
export const causeway = createCausewayResources(client);
```

Importing the generated client registers route contracts with the shared Causeway client types. Resources infer input, data, and error types from the route key.

## Query Resource

```tsx
import { Show } from "solid-js";
import { causeway } from "./causeway";

export function Customer(props: { id: string }) {
  const customer = causeway.query("GET /customers/$id", () => ({
    id: props.id,
  }));

  return (
    <Show when={customer[0]()} fallback={<Skeleton />}>
      {(data) => <h1>{data().name}</h1>}
    </Show>
  );
}
```

The query resource is a normal Solid `ResourceReturn<T>` with an added `error()` accessor.

Input can be a plain object or an accessor. When the accessor changes, Solid re-runs the resource and the Causeway client handles cache identity.

## Mutation Resource

```tsx
const screen = causeway.mutation("POST /customers/$id/screen");

await screen.mutate({ id: props.id });

screen.loading();
screen.error();
screen.data();
screen.reset();
```

Successful mutations run backend-declared `refreshes` through the shared client runtime.

## Subscription Resource

```tsx
const events = createSignal<CustomerEvent[]>([]);

const stream = causeway.subscription(
  "GET /customers/$id/events",
  () => ({ id: props.id }),
  (event) => {
    const [items, setItems] = events;
    setItems([...items(), event]);
  },
);

stream.status(); // "idle" | "connecting" | "open" | "closed" | "error"
stream.error();
```

`subscription` uses `client.stream(...)` and aborts when Solid disposes the effect.

## SolidStart Server Functions

Forward request headers from a server function:

```ts
import { serverQuery } from "@causewayjs/solid/server";
import { client } from "./causeway";

export async function loadCustomer(request: Request, id: string) {
  return await serverQuery(client, "GET /customers/$id", { id }, request);
}
```

## See Also

- [Client runtime](./index.md)
- [Svelte](./svelte.md)
- [`@causewayjs/solid` README](../../packages/causeway-solid/README.md)
