# Svelte

`@causewayjs/svelte` exposes Svelte stores over the same route-key client used by React, Next, and Solid.

```bash
pnpm add @causewayjs/svelte @causewayjs/client svelte
```

## Setup

Create stores from the generated client:

```ts
// src/lib/causeway.ts
import { createCausewayStores } from "@causewayjs/svelte";
import { createClient } from "$lib/generated/causeway/client";

export const client = createClient({ baseUrl: "/api" });
export const causeway = createCausewayStores(client);
```

Importing the generated client registers route contracts with the shared Causeway client types. Stores infer input, data, and error types from the route key.

## Query Store

```svelte
<script lang="ts">
  import { causeway } from "$lib/causeway";

  export let id: string;

  const customer = causeway.query("GET /customers/$id", { id });
</script>

{#if $customer.status === "loading"}
  <Skeleton />
{:else if $customer.status === "error"}
  <ErrorState error={$customer.error} />
{:else if $customer.status === "success"}
  <h1>{$customer.data.name}</h1>
{/if}
```

The query store value has:

- `status`: `"idle" | "loading" | "success" | "error"`
- `data`
- `error`
- `refetch(opts?)`

Pass `{ enabled: false }` when the store should not fetch immediately.

## Mutation Store

```svelte
<script lang="ts">
  const screen = causeway.mutation("POST /customers/$id/screen");

  async function submit() {
    await $screen.mutate({ id });
  }
</script>

<button disabled={$screen.status === "loading"} on:click={submit}>
  Screen
</button>
```

The mutation store value has:

- `status`: `"idle" | "loading" | "success" | "error"`
- `data`
- `error`
- `mutate(vars, opts?)`
- `reset()`

Successful mutations run backend-declared `refreshes` through the shared client runtime.

## Subscription Store

```svelte
<script lang="ts">
  let events: CustomerEvent[] = [];

  const stream = causeway.subscription("GET /customers/$id/events", { id }, (event) => {
    events = [...events, event];
  });
</script>

{#if $stream.status === "connecting"}
  Connecting...
{/if}
```

`subscription` uses `client.stream(...)` and aborts when the store is unsubscribed.

## SvelteKit Server Loads

Forward request headers from server `load` functions:

```ts
import { loadQuery } from "@causewayjs/svelte/server";
import { client } from "$lib/causeway";

export async function load(event) {
  const customer = await loadQuery(
    client,
    "GET /customers/$id",
    { id: event.params.id },
    event,
  );
  return { customer };
}
```

## See Also

- [Client runtime](./index.md)
- [Solid](./solid.md)
- [`@causewayjs/svelte` README](../../packages/causeway-svelte/README.md)
