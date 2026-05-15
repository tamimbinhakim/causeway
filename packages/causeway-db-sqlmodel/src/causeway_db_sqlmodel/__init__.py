"""SQLModel / SQLAlchemy adapter for :class:`causeway.contracts.DBSession`.

Provides an ``AsyncEngine``-backed session factory plus a transaction
context manager. The session itself is exposed as a Causeway scope provider
so handlers pull it via ``Annotated[AsyncSession, db_session]``.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class SqlModelSession:
    contract_version: ClassVar[str] = "v1.0"

    def __init__(self, dsn: str, *, echo: bool = False) -> None:
        self.dsn = dsn
        self.echo = echo
        self._engine: AsyncEngine | None = None
        self._factory: Any = None

    async def startup(self, settings: Any) -> None:  # noqa: ARG002
        self._engine = create_async_engine(self.dsn, echo=self.echo, future=True)
        self._factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def shutdown(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._factory = None

    async def ready(self) -> bool:
        return self._engine is not None

    def session(self) -> contextlib.AbstractAsyncContextManager[AsyncSession]:
        return self._session_ctx()

    @contextlib.asynccontextmanager
    async def _session_ctx(self) -> AsyncIterator[AsyncSession]:
        if self._factory is None:
            msg = "SqlModelSession used before startup()"
            raise RuntimeError(msg)
        async with self._factory() as session:
            yield session

    def transaction(self) -> contextlib.AbstractAsyncContextManager[AsyncSession]:
        return self._transaction_ctx()

    @contextlib.asynccontextmanager
    async def _transaction_ctx(self) -> AsyncIterator[AsyncSession]:
        async with self._session_ctx() as session, session.begin():
            yield session

    async def health(self) -> bool:
        if self._engine is None:
            return False
        try:
            async with self._engine.connect() as conn:
                await conn.exec_driver_sql("SELECT 1")
        except Exception:
            return False
        return True


def plugin(settings: Any) -> None:
    from causeway import register

    dsn = getattr(settings, "database_url", None)
    if not dsn:
        return
    if hasattr(dsn, "get_secret_value"):
        dsn = dsn.get_secret_value()
    register(SqlModelSession(dsn=str(dsn)))


__all__ = ["SqlModelSession", "plugin"]
