# Installation

Get Causeway onto your machine and into a project. This page is the smallest possible "I'm ready to write a handler" loop.

## System requirements

| Tool   | Version | Notes                                                           |
| ------ | ------- | --------------------------------------------------------------- |
| Python | ≥ 3.11  | Causeway uses modern type syntax — `X \| Y`, `Annotated[T, …]`. |
| `uv`   | latest  | Recommended package manager. `brew install uv` on macOS.        |

> **Good to know.** Causeway works with `pip` and `pipx` too — `uv` is just what the docs use because it's faster and ships a lockfile.

## Install into a new project

The fastest path is `causeway new`, which scaffolds the file layout for you.

```bash
uvx --from 'causeway==0.1.0a0' causeway new my-app
cd my-app
uv sync
```

If you'd rather start from `causeway` already in a project:

```bash
uv add 'causeway==0.1.0a0'
```

> **Alpha pin.** Causeway is in `0.1.0a0`. Pinning opts you into the prerelease channel. After `v0.1.0` ships, you can drop the pin.

## Verify the install

```bash
uv run causeway --version
# 0.1.0
```

If you scaffolded with `causeway new`, you can boot the dev server right away:

```bash
uv run causeway dev
```

Open <http://127.0.0.1:8000> and you should see a JSON response from the default route, plus a diagnostics page at <http://127.0.0.1:8000/__causeway>.

## What gets installed

`causeway` pulls in:

- **`starlette`** — the ASGI primitives Causeway composes onto.
- **`pydantic-settings`** — typed config.
- **`structlog`** — structured logging.
- **`typer` + `rich`** — the CLI.
- **`httpx`** — used by the testing kit.

Optional extras:

```bash
uv add 'causeway[otel]'   # OpenTelemetry SDK + ASGI instrumentation
```

## Next steps

- [Project structure](./project-structure.md) — what `causeway new` actually creates and where things live.
- [Your first route](./first-route.md) — write a typed handler, hit it from `curl`, see the generated TypeScript.
