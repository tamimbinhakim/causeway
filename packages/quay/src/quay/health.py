"""Built-in ``/healthz`` and ``/readyz`` endpoints.

- ``/healthz`` returns 200 unconditionally — the process is up.
- ``/readyz`` aggregates every registered plugin's ``ready()`` state. 200
  when all are ready, 503 otherwise. The body is JSON: ``{plugin_name: bool}``.

A user can override either by adding ``routes/healthz.py`` /
``routes/readyz.py`` in their app. Quay's defaults attach only if the path
isn't already in the dyadpy App's route table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dyadpy import Context

from quay.plugins import all_ready

if TYPE_CHECKING:
    from dyadpy import App


async def healthz() -> dict[str, str]:
    """Liveness probe. The process is up — that's all this reports."""
    return {"status": "ok"}


async def readyz(ctx: Context) -> dict[str, object]:
    """Readiness probe — aggregates every registered plugin's ``ready()``.

    Returns 200 with ``{"status": "ready", ...}`` when every plugin reports
    True; 503 with ``{"status": "not_ready", "plugins": {...}}`` otherwise.
    """
    plugins = await all_ready()
    all_ok = all(plugins.values()) if plugins else True
    if not all_ok:
        ctx.set_status(503)
    return {
        "status": "ready" if all_ok else "not_ready",
        "plugins": plugins,
    }


def attach(app: App) -> None:
    """Register ``/healthz`` and ``/readyz`` on the dyadpy App if absent."""
    existing = {(r.method, r.path) for r in app.routes}
    if ("GET", "/healthz") not in existing:
        app.get("/healthz")(healthz)
    if ("GET", "/readyz") not in existing:
        app.get("/readyz")(readyz)


__all__ = ["attach", "healthz", "readyz"]
