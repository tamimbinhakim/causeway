"""Permission expansion and the ``require_permission`` guard.

The default model is ``domain:action`` strings. ``X:manage`` implies
``X:write`` implies ``X:read``; ``*`` is superuser. Plugin authors that want
a different shape ignore these helpers — they exist so the common case
isn't reinvented per project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from causeway.errors import Forbidden, Unauthorized
from causeway.middleware import GuardFn, guard

if TYPE_CHECKING:
    from starlette.requests import Request

    from causeway.contracts import AuthProvider


def expand_permissions(granted: set[str]) -> set[str]:
    """Walk implicit grants. ``X:manage`` → also ``X:write`` + ``X:read``.

    ``*`` short-circuits to a superuser set — callers should check membership
    via :func:`check_permission` rather than iterating the expanded set
    directly, so the superuser short-circuit stays correct.
    """
    if "*" in granted:
        return {"*"}
    out = set(granted)
    for p in granted:
        domain, _, action = p.partition(":")
        if not domain or not action:
            continue
        if action == "manage":
            out.add(f"{domain}:write")
            out.add(f"{domain}:read")
        elif action == "write":
            out.add(f"{domain}:read")
    return out


def check_permission(granted: set[str], required: str) -> bool:
    """Default :meth:`~causeway.contracts.AuthProvider.has_permission` body."""
    expanded = expand_permissions(granted)
    return "*" in expanded or required in expanded


def require_permission(perm: str) -> GuardFn:
    """Guard that 403s a request whose user lacks ``perm``.

    Looks up the registered :class:`~causeway.contracts.AuthProvider` at call
    time so plugin order in ``plugins.py`` doesn't matter. Raises
    :class:`~causeway.errors.Unauthorized` for an anonymous request and
    :class:`~causeway.errors.Forbidden` for an authenticated-but-unprivileged
    one — the error renderer turns those into 401 / 403.
    """

    @guard
    async def _check(req: Request) -> None:
        # Lazy so the module imports cleanly with no registry (codegen, diff, tests).
        from causeway.contracts import AuthProvider as _AuthProvider
        from causeway.plugins import registered

        auth: AuthProvider | None = None
        for adapter in registered():
            if isinstance(adapter, _AuthProvider):
                auth = adapter
                break
        if auth is None:
            msg = "require_permission used but no AuthProvider is registered"
            raise RuntimeError(msg)

        user = await auth.current_user(req)
        if user is None:
            raise Unauthorized("authentication required")
        if not await auth.has_permission(user, perm):
            raise Forbidden(f"requires {perm}")

    _check.__causeway_requires__ = (perm,)  # type: ignore[attr-defined]
    return _check


__all__ = ["check_permission", "expand_permissions", "require_permission"]
