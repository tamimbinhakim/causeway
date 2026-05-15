"""`GET /` — welcome page with site title from Settings."""

from __future__ import annotations

from msgspec import Struct

from quay import get

from app.config import settings


class Welcome(Struct):
    site: str
    env: str


@get
async def root() -> Welcome:
    return Welcome(site=settings.site_title, env=settings.env)
