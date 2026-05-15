"""`PATCH /admin/posts/{id}` · `DELETE /admin/posts/{id}`."""

from typing import Annotated

from msgspec import Struct

from causeway import delete, patch, raises
from causeway.errors import NotFound, Unauthorized

from app.db import AsyncSession, Post, select
from app.deps import current_admin, db_session


class PostPatch(Struct):
    title: str | None = None
    body: str | None = None
    published: bool | None = None


class PostUpdated(Struct):
    id: int
    title: str
    published: bool


@patch
@raises(NotFound, Unauthorized)
async def edit(
    id: int,
    data: PostPatch,
    db: Annotated[AsyncSession, db_session],
    admin: Annotated[str, current_admin],
) -> PostUpdated:
    _ = admin
    row = (await db.execute(select(Post).where(Post.id == id))).scalar_one_or_none()
    if row is None:
        raise NotFound(f"post {id} not found")
    if data.title is not None:
        row.title = data.title
    if data.body is not None:
        row.body = data.body
    if data.published is not None:
        row.published = data.published
    await db.flush()
    return PostUpdated(id=row.id, title=row.title, published=row.published)


@delete
@raises(NotFound, Unauthorized)
async def remove(
    id: int,
    db: Annotated[AsyncSession, db_session],
    admin: Annotated[str, current_admin],
) -> dict[str, bool]:
    _ = admin
    row = (await db.execute(select(Post).where(Post.id == id))).scalar_one_or_none()
    if row is None:
        raise NotFound(f"post {id} not found")
    await db.delete(row)
    return {"deleted": True}
