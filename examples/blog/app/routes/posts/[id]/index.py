"""`GET /posts/{id}` — read a published post with comments."""

from datetime import datetime
from typing import Annotated

from msgspec import Struct
from sqlalchemy.orm import selectinload

from quay import get, raises
from quay.errors import NotFound

from app.db import AsyncSession, Post, select
from app.deps import db_session


class CommentOut(Struct):
    id: int
    author: str
    body: str
    created_at: datetime


class PostDetail(Struct):
    id: int
    title: str
    body: str
    created_at: datetime
    comments: list[CommentOut]


@get
@raises(NotFound)
async def show(id: int, db: Annotated[AsyncSession, db_session]) -> PostDetail:
    stmt = (
        select(Post)
        .where(Post.id == id, Post.published.is_(True))
        .options(selectinload(Post.comments))
    )
    post = (await db.execute(stmt)).scalar_one_or_none()
    if post is None:
        raise NotFound(f"post {id} not found")
    return PostDetail(
        id=post.id,
        title=post.title,
        body=post.body,
        created_at=post.created_at,
        comments=[
            CommentOut(id=c.id, author=c.author, body=c.body, created_at=c.created_at)
            for c in sorted(post.comments, key=lambda c: c.created_at)
        ],
    )
