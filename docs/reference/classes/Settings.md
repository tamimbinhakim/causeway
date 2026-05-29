# `Settings`

A re-export of `pydantic_settings.BaseSettings`. Causeway adds no behavior — it's the same class you'd get from `from pydantic_settings import BaseSettings`.

```python
# src/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")

    env: str = "dev"
    database_url: SecretStr
    redis_url: SecretStr | None = None


settings = Settings()
```

## Why re-export

So application code can write `from causeway import Settings` if it prefers — but for full Pydantic docs (validators, model_config options, `SettingsConfigDict`), the upstream [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) are the source of truth.

## Causeway's expectations

- The instance must live at `app.config.settings` (or `app.settings`).
- Secrets should use `SecretStr` / `SecretBytes`. The framework skips these when surfacing settings to the diagnostics page or the generated TS client, regardless of `causeway.toml`.
- Type annotations matter — they drive parsing and validation.

## See also

- [Configuration](../../app/configuration.md)
- [`Manifest`](./Manifest.md) — the `causeway.toml` counterpart.
- [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
