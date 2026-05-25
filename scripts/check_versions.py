#!/usr/bin/env python3
"""Validate package versions before CI or ad-hoc publishing.

Checks release-please's manifest against package metadata and, on request,
verifies that the tag for the current package version does not already exist.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[a-zA-Z0-9][a-zA-Z0-9._-]*)?$")
PY_INIT_RE = re.compile(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)


@dataclass(frozen=True)
class Package:
    path: Path
    component: str
    name: str
    version: str

    @property
    def tag(self) -> str:
        return f"{self.component}-v{self.version}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="Package path to check, e.g. packages/causeway. Defaults to all release-please packages.",
    )
    parser.add_argument(
        "--check-tag-available",
        action="store_true",
        help="Fail if the package's release tag already exists locally or on origin.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    config = _read_json(root / "release-please-config.json")
    manifest = _read_json(root / ".release-please-manifest.json")
    configured = config.get("packages", {})
    selected = [Path(p) for p in args.packages] if args.packages else [Path(p) for p in configured]

    errors: list[str] = []
    packages: list[Package] = []
    for rel_path in selected:
        path_key = rel_path.as_posix()
        pkg_config = configured.get(path_key)
        if pkg_config is None:
            errors.append(f"{path_key}: missing from release-please-config.json")
            continue
        package_dir = root / rel_path
        if not package_dir.is_dir():
            errors.append(f"{path_key}: package directory does not exist")
            continue
        try:
            package = _read_package(package_dir, pkg_config)
        except ValueError as exc:
            errors.append(f"{path_key}: {exc}")
            continue
        packages.append(package)

        manifest_version = manifest.get(path_key)
        if manifest_version != package.version:
            errors.append(
                f"{path_key}: manifest has {manifest_version!r}, package has {package.version!r}",
            )
        if not VERSION_RE.match(package.version):
            errors.append(f"{path_key}: invalid version {package.version!r}")
        errors.extend(_check_extra_files(package_dir, pkg_config, package.version))

    if args.check_tag_available:
        for package in packages:
            if _tag_exists(root, package.tag):
                errors.append(f"{package.path}: tag {package.tag!r} already exists")

    if errors:
        print("version check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    for package in packages:
        print(f"{package.path.as_posix()} {package.version} ({package.tag})")
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_package(package_dir: Path, config: dict[str, Any]) -> Package:
    pyproject = package_dir / "pyproject.toml"
    if pyproject.exists():
        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
        name = _str(project.get("name"), "project.name")
        version = _str(project.get("version"), "project.version")
    else:
        raise ValueError("expected pyproject.toml")
    component = _str(config.get("component", name), "component")
    return Package(
        path=package_dir.relative_to(package_dir.parents[1]),
        component=component,
        name=name,
        version=version,
    )


def _check_extra_files(package_dir: Path, config: dict[str, Any], version: str) -> list[str]:
    errors: list[str] = []
    for raw in config.get("extra-files", []):
        rel = raw if isinstance(raw, str) else raw.get("path")
        if not rel:
            continue
        extra_path = package_dir / rel
        if not extra_path.exists():
            errors.append(f"{extra_path}: configured extra file does not exist")
            continue
        text = extra_path.read_text(encoding="utf-8")
        match = PY_INIT_RE.search(text)
        if match and match.group(1) != version:
            errors.append(f"{extra_path}: __version__ is {match.group(1)!r}, expected {version!r}")
    return errors


def _tag_exists(root: Path, tag: str) -> bool:
    local = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if local.returncode == 0:
        return True
    remote = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return remote.returncode == 0


def _str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing {name}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
