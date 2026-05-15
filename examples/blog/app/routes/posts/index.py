"""`GET /posts` — list published posts."""

from datetime import datetime
from typing import Annotated

from msgspec import Struct

from quay import get

from app.db import AsyncSession, Post, select
from app.deps import db_session


class PostSummary(Struct):
    id: int
    title: str
    created_at: datetime


@get
async def list_posts(db: Annotated[AsyncSession, db_session]) -> list[PostSummary]:
    stmt = select(Post).where(Post.published.is_(True)).order_by(Post.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [PostSummary(id=p.id, title=p.title, created_at=p.created_at) for p in rows]
