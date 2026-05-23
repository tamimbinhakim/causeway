"""`POST /posts/{id}/comments` — leave a comment; enqueue notify task."""

from datetime import datetime
from typing import Annotated

from msgspec import Struct

from causeway import post, raises
from causeway.errors import BadRequest, NotFound

from app.db import AsyncSession, Comment, Post, select
from app.deps import db_session
from app.tasks import notify_new_comment


class NewComment(Struct):
    author: str
    body: str


class CommentCreated(Struct):
    id: int
    post_id: int
    author: str
    body: str
    created_at: datetime


@post
@raises(NotFound, BadRequest)
async def create(
    id: int,
    data: NewComment,
    db: Annotated[AsyncSession, db_session],
) -> CommentCreated:
    if not data.author.strip() or not data.body.strip():
        raise BadRequest("author and body are required")

    stmt = select(Post).where(Post.id == id, Post.published.is_(True))
    target = (await db.execute(stmt)).scalar_one_or_none()
    if target is None:
        raise NotFound(f"post {id} not found")

    comment = Comment(post_id=id, author=data.author, body=data.body)
    db.add(comment)
    await db.flush()
    await notify_new_comment.enqueue(id, data.author)
    return CommentCreated(
        id=comment.id,
        post_id=id,
        author=comment.author,
        body=comment.body,
        created_at=comment.created_at,
    )
