"""`GET /admin/stats` — counts + recent notifications."""

from typing import Annotated

from msgspec import Struct
from sqlalchemy import func

from causeway import get, raises
from causeway.errors import Unauthorized

from app.db import AsyncSession, Comment, Post, select
from app.deps import current_admin, db_session
from app.notifications import history


class Stats(Struct):
    posts: int
    published: int
    comments: int
    recent_notifications: int


@get
@raises(Unauthorized)
async def stats(
    db: Annotated[AsyncSession, db_session],
    admin: Annotated[str, current_admin],
) -> Stats:
    _ = admin
    posts = (await db.execute(select(func.count()).select_from(Post))).scalar_one()
    published = (
        await db.execute(select(func.count()).select_from(Post).where(Post.published.is_(True)))
    ).scalar_one()
    comments = (await db.execute(select(func.count()).select_from(Comment))).scalar_one()
    return Stats(
        posts=posts,
        published=published,
        comments=comments,
        recent_notifications=len(history()),
    )
