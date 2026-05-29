# Inline scenarios

Co-locate route tests with the routes they test. The route file is the unit of truth — handler, schema, declared errors, and tests all live in one place.

```python
# app/routes/users/index.py
from causeway import get, post, raises
from causeway.errors import BadRequest


@post
@raises(BadRequest)
async def create(data: NewUser) -> User:
    if not data.name or not data.email:
        raise BadRequest("name and email are required")
    return create_user(name=data.name, email=data.email)


if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario

    with scenario("rejects blank fields") as it:
        resp = it.post("/users", json={"name": "", "email": ""})
        expect(resp).body.error.kind == "BadRequest"

    with scenario("creates and reads back") as it:
        new = it.post("/users", json={"name": "ada", "email": "a@x"}).data
        expect(it.get(f"/users/{new.id}")).body.data.email == "a@x"
```

Run with `pytest`. No fixtures to wire, no transport to mount, no separate tests directory to grow.

## Why this exists

Sibling test files solve a different problem — testing across routes. Most route tests don't span routes. They prove that one handler, with one set of inputs, produces one response shape. Putting that test next to the handler keeps the contract visible: when you change the handler, you see the test on the same screen.

The pattern is borrowed from Rust (`#[cfg(test)] mod tests { ... }`), filtered through Python's `if __name__ == ...:` idiom so production imports cost nothing.

## How it runs

1. The Causeway pytest plugin (installed automatically with `causeway`) scans your routes root for `.py` files containing `if __name__ == "__causeway_test__":`.
2. Each `with scenario("label") as it:` block becomes one pytest item: `app/routes/users/index.py::rejects blank fields`.
3. For each item, the plugin imports the route file with `__name__` swapped to `"__causeway_test__"`, builds a fresh `TestApp`, and runs the matching scenario.
4. Other scenarios in the same file are no-ops during that run — every scenario gets its own clean app.

Production imports never trip the guard (`__name__` is the module name there), so the test block has zero runtime cost in real deploys.

## The `it` client

`it` is a synchronous fluent client over `httpx.AsyncClient(ASGITransport(app))`. Every HTTP method drives a fresh event loop under the hood — you write straight-line code, no `await`.

```python
with scenario("…") as it:
    it.get("/users")            # Response
    it.post("/users", json={…}) # Response
    it.put("/users/1", json={…})
    it.patch("/users/1", json={…})
    it.delete("/users/1")
    it.request("OPTIONS", "/users")

    it.last           # most recent Response
    it.app            # underlying causeway.App (escape hatch)

    # DI / tasks
    it.override(get_session, lambda: fake_session)
    it.tasks_eager()

    # Control flow
    it.skip("not implemented yet")
    it.xfail("known bug #42")
```

Each scenario gets its own `TestApp`, so state from one scenario can't leak into the next.

## The `expect` proxy

`expect(...)` returns a chainable assertion proxy. Attribute / item access walks into the response; comparison operators fire the assertion.

```python
expect(it.get("/users")).body == [{"id": 1, "name": "ada"}]
expect(it).body.data.name == "ada"          # implicitly `it.last`
expect(it).body.error.kind == "BadRequest"
expect(it).body.items[0].name == "ada"      # walk lists by index
expect(it).status == 200
expect(it).body.count >= 1
expect("foo") in expect(it).body.tags

# Explicit predicates for when operators don't fit
expect(it).body.id.matches(lambda x: isinstance(x, int))
expect(it).body.email.is_not(None)
```

On failure you get a unified diff anchored to the path:

```
values differ
  in /app/routes/users/index.py::rejects blank fields
  at .body.error.kind
--- expected
+++ actual
@@ -1 +1 @@
-'BadRequest'
+'NotFound'
```

## Snapshots

For response shapes too tedious to type by hand, use `snapshot(...)`. On first run with `--update-snapshots`, the literal in your source gets rewritten in place with the actual value. On subsequent runs it's a normal equality check.

```python
from causeway.testing import expect, scenario, snapshot

with scenario("returns the standard envelope") as it:
    expect(it.get("/users/1")).body == snapshot()  # first run with --update
```

After `pytest --update-snapshots`:

```python
expect(it.get("/users/1")).body == snapshot({
    "ok": True,
    "data": {"id": 1, "name": "ada", "email": "a@x"},
})
```

Use `...` as a wildcard for any field that varies between runs:

```python
expect(it.get("/users/1")).body == snapshot({
    "ok": True,
    "data": {"id": ..., "name": "ada", "email": ...},
})
```

A bare `snapshot()` without a recorded value fails until you run with `--update-snapshots` — so a teammate who fetches your branch won't silently record their own values.

## CLI flags

| Flag                     | Effect                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| `--causeway-routes=PATH` | Routes root to scan. Repeatable. Default: discovered from `causeway.toml` siblings, else `app/routes`. |
| `--update-snapshots`     | Record snapshots that have no value yet; rewrite mismatched ones.                                      |
| `--causeway-no-inline`   | Skip inline collection entirely.                                                                       |

For convenience, pin the routes root in `pyproject.toml` instead of typing it every time:

```toml
[tool.pytest.ini_options]
addopts = ["--causeway-routes=app/routes"]
```

## When _not_ to use inline scenarios

Inline scenarios are for single-route tests. Two patterns push toward an external test file:

1. **Cross-route flows.** A test that hits `POST /users` then `GET /accounts/{id}` is testing how routes compose. Put it in `tests/`.
2. **Heavy fixtures.** A scenario that needs a real database, a Redis fake, or a complex DI setup belongs in `tests/` with proper fixtures — the inline DSL deliberately keeps its surface small.

Both patterns coexist. The example in `examples/minimal-crud` keeps one external `tests/test_users.py` to demonstrate the escape hatch.

## Caveats

- **Async user code in scenario bodies is not supported.** Scenarios are synchronous — they drive async ASGI under the hood. If you need to `await` something custom, do it via a DI override or a helper in `_scope.py`.
- **The scenario body runs once during collection** (with a no-op `it`) so the plugin can enumerate scenarios. Top-level helpers in your body run twice — once for collection, once for the targeted run. Keep bodies light; for heavy setup, guard on `it.collecting`.
- **Pyright / mypy don't trace fluent proxies.** `expect(it).body.data.name == "ada"` is `Any`-typed by design. That's the cost of the DSL; we accept it inside scenario bodies because they're tests, not production code.
- **Coverage tools.** Add `if __name__ == "__causeway_test__":` to `[tool.coverage.report] exclude_also` so the block doesn't show as uncovered in production reports.

## Listing

```text
$ pytest --collect-only --causeway-routes app/routes
<RouteFileCollector app/routes/users/index.py>
  <ScenarioItem lists empty>
  <ScenarioItem creates and reads back>
  <ScenarioItem rejects blank fields>
<RouteFileCollector app/routes/users/$id.py>
  <ScenarioItem show returns 404 envelope when missing>
  <ScenarioItem edit renames an existing user>
  <ScenarioItem delete removes the user>
```

Standard pytest selection works:

```text
pytest -k "rejects blank"
pytest "app/routes/users/index.py::rejects blank fields"
```

## See also

- [Testing overview](./testing.md)
- [Defining routes](../backend/routing.md)
- [Internals: testing strategy](../internals/testing.md)
