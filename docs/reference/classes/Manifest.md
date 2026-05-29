# `Manifest`

Parsed `causeway.toml`. A frozen dataclass with two fields.

```python
from causeway.config import load_manifest

m = load_manifest("causeway.toml")
m.expose_settings    # ("env", "feature_flags")
m.app                # {"name": "my-app", "description": "..."}
```

## Shape

```python
@dataclass(frozen=True, slots=True)
class Manifest:
    expose_settings: tuple[str, ...] = ()
    app: dict[str, Any] = {}
```

## Loading

```python
load_manifest(path: str | Path = "causeway.toml") -> Manifest
```

A missing file returns the default (empty) manifest — `causeway.toml` is optional.

## The TOML shape

```toml
# causeway.toml
[app]
name = "my-app"
description = "Hello from Causeway"

[client]
expose_settings = ["env", "feature_flags"]
```

| Field                      | Purpose                                                                       |
| -------------------------- | ----------------------------------------------------------------------------- |
| `[client] expose_settings` | Allowlist of non-secret settings fields to bake into the generated TS client. |
| `[app]`                    | Arbitrary metadata (name, description) — surfaced in diagnostics.             |

> **Good to know.** Secrets (`SecretStr`, `SecretBytes`) are **never** exposed to the TS client, even if listed in `expose_settings`. Defense in depth.

## See also

- [Configuration](../../app/configuration.md)
- [`Settings`](./Settings.md)
- [`causeway.toml`](../file-conventions/causeway-toml.md)
