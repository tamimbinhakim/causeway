"""Config + quay.toml manifest tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from quay.config import Manifest, expose_for_client, load_manifest


def _write(path: Path, body: str) -> None:
    path.write_text(body)


def test_missing_manifest_returns_default(tmp_path: Path) -> None:
    assert load_manifest(tmp_path / "quay.toml") == Manifest()


def test_parses_expose_settings(tmp_path: Path) -> None:
    m = tmp_path / "quay.toml"
    _write(
        m,
        '[client]\nexpose_settings = ["env", "feature_flags"]\n[app]\nname = "demo"\n',
    )
    parsed = load_manifest(m)
    assert parsed.expose_settings == ("env", "feature_flags")
    assert parsed.app == {"name": "demo"}


def test_invalid_expose_settings_rejected(tmp_path: Path) -> None:
    m = tmp_path / "quay.toml"
    _write(m, "[client]\nexpose_settings = [1, 2]\n")
    with pytest.raises(ValueError, match="list of strings"):
        load_manifest(m)


def test_expose_for_client_skips_secrets() -> None:
    from pydantic import SecretStr
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class S(BaseSettings):
        model_config = SettingsConfigDict()
        env: str = "dev"
        api_key: SecretStr = SecretStr("hidden")
        feature_flags: dict[str, bool] = {"new_ui": True}

    out = expose_for_client(
        S(),
        Manifest(expose_settings=("env", "api_key", "feature_flags", "nonexistent")),
    )
    assert out == {"env": "dev", "feature_flags": {"new_ui": True}}


def test_expose_for_client_no_settings_yields_empty() -> None:
    assert expose_for_client(None, Manifest(expose_settings=("env",))) == {}
