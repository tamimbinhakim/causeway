"""Path-aware wrapper around ``httpx.Response`` for the inline-scenario DSL."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class _Missing:
    """Sentinel value for an absent JSON path. Equal to nothing."""

    __slots__ = ("path",)

    def __init__(self, path: tuple[str, ...]) -> None:
        self.path = path

    def __repr__(self) -> str:
        return f"<missing .{'.'.join(self.path)}>"

    def __eq__(self, _other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return id(self)


class PathValue:
    """A value reached by walking attribute / item access on a response.

    Operators (``==`` / ``!=`` / ``<`` / ``>`` / ``in``) are not handled
    here — :class:`~causeway._testing.expect.Expectation` adds them. This
    type's only job is to traverse and carry the path for error messages.
    """

    __slots__ = ("_value", "path", "response")

    def __init__(
        self,
        value: Any,
        *,
        path: tuple[str, ...],
        response: Response,
    ) -> None:
        self._value = value
        self.path = path
        self.response = response

    def __getattr__(self, name: str) -> PathValue:
        return self[name]

    def __getitem__(self, key: Any) -> PathValue:
        new_path = (*self.path, str(key))
        value = self._value
        if isinstance(value, _Missing):
            return PathValue(value, path=new_path, response=self.response)
        if isinstance(value, dict):
            return PathValue(
                value.get(key, _Missing(new_path)),
                path=new_path,
                response=self.response,
            )
        if isinstance(value, list):
            try:
                idx = int(key)
            except (TypeError, ValueError):
                return PathValue(_Missing(new_path), path=new_path, response=self.response)
            if 0 <= idx < len(value):
                return PathValue(value[idx], path=new_path, response=self.response)
            return PathValue(_Missing(new_path), path=new_path, response=self.response)
        if isinstance(key, str) and hasattr(value, key):
            return PathValue(getattr(value, key), path=new_path, response=self.response)
        return PathValue(_Missing(new_path), path=new_path, response=self.response)

    def unwrap(self) -> Any:
        return self._value

    def __repr__(self) -> str:
        return f"PathValue({self._value!r}, path={self.path!r})"


class Response:
    """Wraps an ``httpx.Response`` with attribute-walking accessors.

    Most of the work is delegated to ``httpx.Response``; we just add:

    - ``.body`` — parsed JSON body as a :class:`PathValue` for nice diffs.
    - ``.status`` — alias for ``.status_code`` (shorter in scenario code).
    - ``.data`` — shortcut for ``.body.data`` (Causeway's envelope).
    - ``.error`` — shortcut for ``.body.error``.
    """

    __slots__ = ("_body_cache", "_raw")

    def __init__(self, raw: httpx.Response) -> None:
        self._raw = raw
        self._body_cache: Any = _UNCACHED

    @property
    def raw(self) -> httpx.Response:
        return self._raw

    @property
    def status_code(self) -> int:
        return self._raw.status_code

    @property
    def status(self) -> int:
        return self._raw.status_code

    @property
    def headers(self) -> Any:
        return self._raw.headers

    @property
    def text(self) -> str:
        return self._raw.text

    def json(self) -> Any:
        if self._body_cache is _UNCACHED:
            try:
                self._body_cache = self._raw.json()
            except (json.JSONDecodeError, ValueError):
                self._body_cache = None
        return self._body_cache

    @property
    def body(self) -> PathValue:
        return PathValue(self.json(), path=("body",), response=self)

    @property
    def data(self) -> PathValue:
        return self.body["data"]

    @property
    def error(self) -> PathValue:
        return self.body["error"]

    def __repr__(self) -> str:
        return f"Response(status={self.status_code}, body={self.json()!r})"


_UNCACHED: Any = object()
