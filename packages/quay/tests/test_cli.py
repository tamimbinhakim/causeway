"""CLI smoke tests via Typer's CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from quay.cli import app

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_plugins_empty() -> None:
    from quay.plugins import clear

    clear()
    result = runner.invoke(app, ["plugins"])
    assert result.exit_code == 0
    assert "no plugins" in result.stdout.lower()


def test_new_scaffolds_expected_files(tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "demo", "--target", str(tmp_path)])
    assert result.exit_code == 0

    root = tmp_path / "demo"
    assert (root / "pyproject.toml").is_file()
    assert (root / "quay.toml").is_file()
    assert (root / "app" / "app.py").is_file()
    assert (root / "app" / "routes" / "index.py").is_file()
    assert (root / "tests" / "test_smoke.py").is_file()

    # The scaffolded pyproject names the project correctly.
    pyproject = (root / "pyproject.toml").read_text()
    assert 'name = "demo"' in pyproject


def test_new_refuses_existing_dir(tmp_path: Path) -> None:
    (tmp_path / "demo").mkdir()
    result = runner.invoke(app, ["new", "demo", "--target", str(tmp_path)])
    assert result.exit_code != 0
    assert "already exists" in result.stdout
