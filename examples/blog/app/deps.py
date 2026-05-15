"""Scope providers — declared once, imported by both `_scope.py` files
(for registration) and route handlers (for `Annotated[T, provider]`).

Defining providers here keeps them addressable as a normal Python module.
The file router matches `Annotated[Session, db_session]` to the
registered provider by `(filename, qualname)`, so as long as the same
function object is referenced everywhere, the wiring just works.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from starlette.requests import Request

from causeway import provide
from causeway.errors import Unauthorized

from app.config import settings
from app.db import AsyncSession, SessionFactory


@provide("db")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Per-request SQLAlchemy session. Commits on clean return, rolls back on error."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@provide("admin")
async def current_admin(req: Request) -> str:
    """Resolve the bearer token off the request, or raise Unauthorized.

    The admin guard in `(admin)/_middleware.py` already rejects un-tokened
    requests, but having a provider lets handlers depend on the live token
    when they need it (audit logs, etc.).
    """
    header = req.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthorized("missing bearer token")
    token = header.removeprefix("Bearer ").strip()
    if token != settings.admin_token.get_secret_value():
        raise Unauthorized("invalid token")
    return token
