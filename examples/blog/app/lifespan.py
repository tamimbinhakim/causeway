"""App-wide startup / shutdown."""

from __future__ import annotations

import logging

from app.db import create_all, dispose

_log = logging.getLogger("blog.lifespan")


async def startup() -> None:
    await create_all()
    _log.info("blog: ready")


async def shutdown() -> None:
    await dispose()
    _log.info("blog: stopped")
