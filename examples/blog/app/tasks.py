"""Background tasks.

`@task` registers a coroutine with the active adapter; callers enqueue
via `task_ref.enqueue(...)`. `@cron` schedules one on a crontab
expression. The reference `InMemoryAdapter` (wired in `plugins.py`)
runs tasks in the same event loop — swap it for Dramatiq / Celery /
Arq by registering a different adapter in `plugins.py`.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete

from quay import cron, task

from app.db import Comment, SessionFactory
from app.notifications import record

_log = logging.getLogger("blog.tasks")


@task(queue="emails", retries=3, backoff="exponential")
async def notify_new_comment(post_id: int, author: str) -> None:
    """Pretend to email the post author."""
    record("new_comment", post_id=post_id, author=author)
    _log.info("notified about comment on post %s by %s", post_id, author)


@cron("*/5 * * * *")
async def purge_spam_drafts() -> None:
    """Reap any comment whose body equals the literal string `__spam__`.

    Cosmetic — real spam detection is out of scope; this just shows where
    cron logic lives.
    """
    async with SessionFactory() as session:
        await session.execute(delete(Comment).where(Comment.body == "__spam__"))
        await session.commit()
