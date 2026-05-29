# `causeway new`

Scaffold a new Causeway app.

```bash
causeway new my-app
```

## Synopsis

```
causeway new <name> [--target <dir>]
```

## Arguments

| Argument          | Default     | Description                                             |
| ----------------- | ----------- | ------------------------------------------------------- |
| `<name>`          | —           | Project directory name (also becomes the package name). |
| `--target` / `-t` | current dir | Parent directory to create the project under.           |

## What it creates

```
my-app/
├── pyproject.toml
├── causeway.toml
├── .env / .env.example
└── src/app/
    ├── __init__.py
    ├── config.py            # Settings(BaseSettings)
    ├── plugins.py           # register(...) calls
    ├── lifespan.py          # optional app-level startup / shutdown
    └── routes/
        ├── _middleware.py   # RequestId etc.
        └── index.py         # GET / handler
```

## Next steps after running

```bash
cd my-app
uv sync
causeway dev
```

## Errors

- The target directory must not already exist.
- The name must be a valid Python package identifier (alphanumeric, underscore, hyphen).

## See also

- [Project structure](../../start/project-structure.md)
- [Your first route](../../start/first-route.md)
