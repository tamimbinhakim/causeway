# `discover`

Walk a routes directory and return a `Discovered` snapshot. Low-level — most apps use [`create_app`](./create-app.md), which calls this internally.

```python
from causeway.routing import discover

found = discover("src/app/routes")
for route in found.routes:
    print(route.method, route.route_key, route.path, route.source)
```

## Signature

```python
discover(routes_root: str | Path) -> Discovered
```

Raises `FileNotFoundError` if `routes_root` doesn't exist.

## Return value

```python
@dataclass
class Discovered:
    routes: list[DiscoveredRoute]
    startup_hooks: list[Callable[[], Awaitable[None]]]
    shutdown_hooks: list[Callable[[], Awaitable[None]]]


@dataclass
class DiscoveredRoute:
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str                        # e.g. "/users/{id}"
    route_key: str                   # e.g. "GET /users/$id"
    handler: Callable
    middleware: list                 # @guard fns + Middleware instances
    providers: dict[str, Callable]   # @provide names → fns
    source: Path                     # source file path
    scopes: tuple[str, ...]
    refreshes: tuple[str, ...]
    requires: tuple[str, ...]
    idempotency: dict[str, Any] | None
```

## Properties

- **Pure.** No global state mutated, no `causeway.App` touched.
- **Sorted by specificity.** `Discovered.routes` is re-sorted so literal segments outrank parametric (`{name}`) ones at every depth — `/users/me` always registers before `/users/{id}` regardless of filesystem walk order. Ties preserve walk order (stable sort).
- **Boot-checked.** Method conflicts (two `@get` for the same URL) raise `TypeError` here, not at request time.

## Use cases

- **Snapshot tests** for the route table:
  ```python
  found = discover("src/app/routes")
  assert {r.route_key for r in found.routes} == EXPECTED
  ```
- **Custom registration.** Hand the snapshot to your own `causeway.App` if you want to compose differently.
- **CI introspection.** Print the route table during build for review diffs.

## See also

- [`register`](./register.md) — wires a `Discovered` snapshot onto a `causeway.App`.
- [`create_app`](./create-app.md) — the high-level wrapper most apps use.
- [Architecture — boot pipeline](../../architecture/boot-pipeline.md)
