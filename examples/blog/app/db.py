"""SQLAlchemy engine + ORM models.

One process-wide async engine, one async sessionmaker. Route handlers
get a session via `_scope.py`'s `@provide("db")` provider; the
provider yields a session and rolls back / closes on the way out.

Models are deliberately tiny — the point is to show Causeway's wiring, not
SQLAlchemy patterns.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    comments: Mapped[list[Comment]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
    )


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    post: Mapped[Post] = relationship(back_populates="comments")


engine = create_async_engine(settings.database_url, future=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def create_all() -> None:
    """Create tables if they don't exist. Called from app lifespan."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose() -> None:
    """Tear down the engine pool. Called from app lifespan."""
    await engine.dispose()


__all__ = [
    "AsyncSession",
    "Base",
    "Comment",
    "Post",
    "SessionFactory",
    "create_all",
    "dispose",
    "select",
]
