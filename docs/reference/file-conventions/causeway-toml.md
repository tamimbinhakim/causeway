# `causeway.toml`

Framework manifest. Lives at the project root next to `pyproject.toml`. Optional in v0.1.

```toml
# causeway.toml
[app]
name = "my-app"
description = "Hello from Causeway"

[client]
expose_settings = ["env", "feature_flags"]
```

## Sections

### `[app]`

Free-form metadata. Surfaced on the diagnostics page (`/__causeway`) and used by the scaffolder.

| Key           | Type   | Notes                             |
| ------------- | ------ | --------------------------------- |
| `name`        | string | Project name.                     |
| `description` | string | One-line description.             |
| anything else | any    | Available in `Manifest.app` dict. |

### `[client]`

Controls what the TS client gets.

| Key               | Type      | Default | Notes                                                                      |
| ----------------- | --------- | ------- | -------------------------------------------------------------------------- |
| `expose_settings` | list[str] | `[]`    | Allowlist of non-secret settings fields to bake into the generated client. |

## Secrets are never exposed

Even if you list a `SecretStr` field in `expose_settings`, it's filtered before codegen. This is defense in depth — don't rely on the allowlist alone.

## Loading

```python
from causeway.config import load_manifest

m = load_manifest("causeway.toml")
m.expose_settings   # ("env", "feature_flags")
```

A missing file returns an empty `Manifest()`.

## See also

- [Configuration](../../app/configuration.md)
- [`Manifest`](../classes/Manifest.md)
- [Client runtime](../../client/index.md)
