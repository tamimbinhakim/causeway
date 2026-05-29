# @causewayjs/solid

SolidJS resources for the Causeway route-key client.

```bash
pnpm add @causewayjs/solid @causewayjs/client solid-js
```

```tsx
import { createCausewayResources } from "@causewayjs/solid";
import { createClient } from "./client";

const resources = createCausewayResources(createClient({ baseUrl: "/api" }));
const [issue] = resources.query("GET /issues/$issue_id", () => ({
  issueId: 1,
}));

export default function Issue() {
  return (
    <Show when={issue()} fallback={<p>Loading...</p>}>
      <h1>{issue()!.title}</h1>
    </Show>
  );
}
```

Import the generated client once and `query`, `mutation`, and `subscription`
infer `input`, `data`, and `error` from the route key. The shared owned client
runtime keeps refreshes and typed `CausewayError` behavior aligned with React
and Svelte.

## Docs

See the full Solid guide in the Causeway docs: <https://github.com/tamimbinhakim/causeway/blob/main/docs/client/solid.md>.

## License

MIT
