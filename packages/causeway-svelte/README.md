# @causewayjs/svelte

Svelte stores for the Causeway route-key client.

```bash
pnpm add @causewayjs/svelte @causewayjs/client svelte
```

```svelte
<script lang="ts">
  import { createCausewayStores } from "@causewayjs/svelte";
  import { createClient } from "$lib/causeway/client";

  const stores = createCausewayStores(createClient({ baseUrl: "/api" }));
  const issue = stores.query("GET /issues/$issue_id", { issueId: 1 });
</script>

{#if $issue.status === "loading"}
  Loading...
{:else if $issue.status === "success"}
  {$issue.data.title}
{:else if $issue.status === "error"}
  Failed: {$issue.error.message}
{/if}
```

Import the generated client once and `query`, `mutation`, and `subscription`
infer `input`, `data`, and `error` from the route key. The shared owned client
runtime keeps refreshes and typed `CausewayError` behavior aligned with React
and Solid.

## Docs

See the full Svelte guide in the Causeway docs: <https://github.com/tamimbinhakim/causeway/blob/main/docs/client/svelte.md>.

## License

MIT
