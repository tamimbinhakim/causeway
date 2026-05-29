# App Graph

The App Graph is Causeway's metadata view of your application. The IR answers "what is the wire contract?" The App Graph answers "what did the framework discover?"

It is metadata only. Requests still execute through the normal runtime.

## What It Contains

The graph includes:

- Routes: route key, HTTP path, method, source file, route-group scopes, params, response, declared errors, stream marker, and refresh contracts.
- Middleware and providers attached through `_middleware.py` and `_scope.py`.
- Permission requirements exposed by permission guards.
- Idempotency settings exposed by idempotency middleware.
- Registered plugins and contract versions.
- Background tasks and cron registrations.
- Events, listeners, subscribers, and webhook capability.

This is the shape Causeway exposes to dev tools, generated metadata, and agents. It lets the framework talk about the app without asking the app to invent a second registry.

## Example

```python
# src/app/routes/(org)/customers/$id/screen.py
from causeway import post, raises, require_permission, use
from causeway.errors import NotFound

@post(refreshes=("GET /customers/$id", "GET /customers"))
@use(require_permission("compliance:write"))
@raises(NotFound)
async def screen(id: UUID) -> Screening: ...
```

The route entry includes:

```json
{
  "route_key": "POST /customers/$id/screen",
  "method": "POST",
  "http_path": "/customers/{id}/screen",
  "source": "src/app/routes/(org)/customers/$id/screen.py",
  "scopes": ["org"],
  "errors": ["NotFound"],
  "refreshes": ["GET /customers/$id", "GET /customers"],
  "requires": ["compliance:write"]
}
```

## Inspecting It

From the CLI:

```bash
causeway inspect
causeway inspect --json
```

In dev:

```text
http://127.0.0.1:8000/__causeway/graph
```

The JSON endpoint is dev-only. It is meant for local tooling, tests, and AI-assisted development workflows, not as a production API.

## Why It Exists

Causeway already knows a lot after discovery:

- which file produced a route,
- which route group scopes it belongs to,
- which middleware wraps it,
- which permission guard protects it,
- which mutation refreshes which query,
- which provider names are available in the subtree.

Without the App Graph, that knowledge would be trapped inside runtime objects. With the graph, docs, diagnostics, agents, codegen, and future tooling can all read the same application shape.

## IR vs App Graph

| Question                           | Use        |
| ---------------------------------- | ---------- |
| What TypeScript type is returned?  | IR         |
| Is this route a query or mutation? | IR + graph |
| Which source file owns the route?  | App Graph  |
| Which group scopes apply?          | App Graph  |
| Which mutation refreshes this?     | App Graph  |
| Did a response schema break?       | IR         |
| Which plugins/tasks/events exist?  | App Graph  |

The two are siblings, not competitors. The IR keeps the wire contract stable; the App Graph keeps the application shape visible.

## See Also

- [Client runtime](./index.md)
- [Defining routes](../backend/routing.md)
- [`causeway inspect`](../reference/cli/inspect.md)
