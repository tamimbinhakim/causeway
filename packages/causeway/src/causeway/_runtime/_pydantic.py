"""Pydantic interop — first-class peer to msgspec.

Detection is lazy: we never import ``pydantic`` at module-load time. If a
handler annotates a parameter or return value with a ``BaseModel`` subclass
we'll catch it via ``is_pydantic_model`` and route validation + schema
extraction through Pydantic. msgspec stays the default; Pydantic plugs in.
"""

from __future__ import annotations

from typing import Any

_cached_base_model: Any = None
_import_tried = False


def _try_import() -> Any:
    """Return ``pydantic.BaseModel`` or ``None`` if Pydantic isn't installed.

    Cached so the import attempt only happens once per process.
    """
    global _cached_base_model, _import_tried
    if _import_tried:
        return _cached_base_model
    _import_tried = True
    try:
        from pydantic import BaseModel
    except ImportError:
        return None
    _cached_base_model = BaseModel
    return BaseModel


def is_pydantic_model(t: object) -> bool:
    base = _try_import()
    if base is None:
        return False
    try:
        return isinstance(t, type) and issubclass(t, base)
    except TypeError:
        return False


def validate(t: type, value: Any) -> Any:
    """Run a value through Pydantic validation. Caller asserts ``t`` is a model."""
    return t.model_validate(value)  # type: ignore[attr-defined]


def json_schema(t: type, *, mode: str = "validation") -> dict[str, Any]:
    """Return the Pydantic-emitted JSON schema for a model.

    ``mode`` is ``"validation"`` (default — for request bodies; required
    fields are required, computed fields excluded) or ``"serialization"``
    (for response types; computed fields included, defaults applied).
    """
    return t.model_json_schema(mode=mode)  # type: ignore[attr-defined,no-any-return]


def to_jsonable(value: Any) -> Any:
    """Convert a Pydantic instance to plain JSON-able dict; pass-through otherwise."""
    base = _try_import()
    if base is None or not isinstance(value, base):
        return value
    return value.model_dump(mode="json")
