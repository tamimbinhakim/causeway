"""`GET /admin/posts` (incl. drafts) · `POST /admin/posts`."""

from datetime import datetime
from typing import Annotated

from app.db import AsyncSession, Post, select
from app.deps import current_admin, db_session
from msgspec import Struct
from causeway import get, post, raises
from causeway.errors import BadRequest, Unauthorized


class AdminPostRow(Struct):
    id: int
    title: str
    published: bool
    created_at: datetime


class NewPost(Struct):
    title: str
    body: str
    published: bool = False


class PostCreated(Struct):
    id: int
    title: str
    published: bool


@get
@raises(Unauthorized)
async def list_all(
    db: Annotated[AsyncSession, db_session],
    admin: Annotated[str, current_admin],
) -> list[AdminPostRow]:
    _ = admin  # the provider raises Unauthorized when the token is bad
    stmt = select(Post).order_by(Post.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [
        AdminPostRow(
            id=p.id, title=p.title, published=p.published, created_at=p.created_at
        )
        for p in rows
    ]


@post
@raises(BadRequest, Unauthorized)
async def create(
    data: NewPost,
    db: Annotated[AsyncSession, db_session],
    admin: Annotated[str, current_admin],
) -> PostCreated:
    _ = admin
    if not data.title.strip() or not data.body.strip():
        raise BadRequest("title and body are required")
    row = Post(title=data.title, body=data.body, published=data.published)
    db.add(row)
    await db.flush()
    return PostCreated(id=row.id, title=row.title, published=row.published)
