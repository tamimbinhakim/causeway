# @causewayjs/solid

SolidJS resource bindings for [Causeway](https://github.com/tamimbinhakim/causeway)-generated
clients. Three factory functions on top of the typed `api`:

| Resource       | What it does                                                               |
| -------------- | -------------------------------------------------------------------------- |
| `query`        | `createResource`-backed unary call; reactive on the args accessor.         |
| `mutation`     | Imperative `mutate(args)` with `data`/`error`/`loading` signals.           |
| `subscription` | Subscribes to a `stream[T]` endpoint; events forwarded to an `onEvent` cb. |

## Install

```bash
pnpm add @causewayjs/solid @causewayjs/ts solid-js
```

## Use

```tsx
import { createCausewayResources } from "@causewayjs/solid";
import { api } from "./lib/dyadpy/client";

const resources = createCausewayResources(api);
const [issue] = resources.query("getIssue", () => ({ issueId: 1 }));

export default function Issue() {
  return (
    <Show when={issue()} fallback={<p>Loading…</p>}>
      <h1>{issue()!.title}</h1>
    </Show>
  );
}
```

For a `@raises(...)` route the `error` accessor on the query carries the
typed discriminated union.

## License

MIT
