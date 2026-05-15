"""App-root scope.

The root `_scope.py` fires once per process at startup / shutdown.
Subtrees may declare their own `_scope.py` files with their own
providers and lifecycle hooks; those compose with this one.
"""

from __future__ import annotations

from quay.plugins import shutdown_all, startup_all

from app.config import settings
from app.lifespan import shutdown as _lifespan_shutdown
from app.lifespan import startup as _lifespan_startup


async def startup() -> None:
    await _lifespan_startup()
    await startup_all(settings)


async def shutdown() -> None:
    await shutdown_all()
    await _lifespan_shutdown()
