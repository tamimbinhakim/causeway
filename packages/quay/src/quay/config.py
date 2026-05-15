"""Typed config.

Quay's ``Settings`` is just ``pydantic_settings.BaseSettings`` with one wrapper
added: ``load(module)`` finds a ``settings`` instance in the given app module
(or ``app.config``) and returns it. The wrapper is small on purpose — anything
``pydantic-settings`` already does, we don't re-do.

The ``quay.toml`` file is read separately by :func:`load_manifest`. The only
keys we look at are ``[client].expose_settings`` (allowlist of non-secret
fields to surface to the generated TS client) and ``[app]`` metadata.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings


def _empty_app() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True)
class Manifest:
    """Parsed ``quay.toml``. Fields default to empty when the file is absent."""

    expose_settings: tuple[str, ...] = ()
    app: dict[str, Any] = field(default_factory=_empty_app)


def load_manifest(path: str | Path = "quay.toml") -> Manifest:
    """Read ``quay.toml`` and return a :class:`Manifest`.

    A missing file returns the default (empty) manifest rather than erroring —
    the file is optional in v0.1.
    """
    p = Path(path)
    if not p.is_file():
        return Manifest()
    with p.open("rb") as f:
        data = tomllib.load(f)
    client = data.get("client", {}) or {}
    exposed = client.get("expose_settings", []) or []
    if not isinstance(exposed, list) or not all(isinstance(s, str) for s in exposed):
        msg = "[client] expose_settings must be a list of strings"
        raise ValueError(msg)
    app = data.get("app", {}) or {}
    return Manifest(expose_settings=tuple(exposed), app=app)


def load_settings(app_module: str) -> BaseSettings | None:
    """Locate the app's ``settings`` instance.

    Tries ``{app_module}.config.settings`` first, then ``{app_module}.settings``.
    Returns ``None`` if neither is defined — the rest of the framework treats
    config as optional in v0.1 so a hello-world app needs zero env wiring.
    """
    for candidate in (f"{app_module}.config", app_module):
        try:
            mod = import_module(candidate)
        except ModuleNotFoundError:
            continue
        settings = getattr(mod, "settings", None)
        if isinstance(settings, BaseSettings):
            return settings
    return None


def expose_for_client(settings: BaseSettings | None, manifest: Manifest) -> dict[str, Any]:
    """Pick out the non-secret settings keys to ship to the generated client.

    Anything in ``manifest.expose_settings`` is included as long as it exists
    on the settings instance. Pydantic ``SecretStr`` / ``SecretBytes`` values
    are still skipped (defense in depth — never trust the allowlist alone).
    """
    if settings is None:
        return {}
    out: dict[str, Any] = {}
    for key in manifest.expose_settings:
        if not hasattr(settings, key):
            continue
        value = getattr(settings, key)
        type_name = type(value).__name__
        if type_name in {"SecretStr", "SecretBytes"}:
            continue
        out[key] = value
    return out


# Annotated so downstream type checkers see a complete type even when
# ``pydantic-settings`` ships without ``py.typed``.
Settings: type[BaseSettings] = BaseSettings


__all__ = [
    "BaseSettings",
    "Manifest",
    "Settings",
    "expose_for_client",
    "load_manifest",
    "load_settings",
]
