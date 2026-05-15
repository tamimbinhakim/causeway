"""App settings.

`Settings` is a pydantic-settings model, loaded once at import. Missing
required fields fail fast with a clear error. The `expose_settings` list
in `causeway.toml` decides which non-secret keys are shipped to the TS client.
"""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    site_title: str = "My Causeway Blog"
    database_url: str = "sqlite+aiosqlite:///./blog.db"
    admin_token: SecretStr = SecretStr("changeme-in-prod")


settings = Settings()
