"""``/__quay`` diagnostics endpoint.

A single JSON endpoint that surfaces everything Quay knows about the running
app: route tree, registered tasks, cron jobs, registered plugins, and the
non-secret config that the manifest allows on the wire.

The endpoint is wired by :func:`attach`, which the dev loop calls
automatically. Production apps can attach it manually if they want, but
it's not registered by default.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from quay.config import Manifest, expose_for_client
from quay.plugins import registered
from quay.tasks import cron_jobs, registered_tasks

if TYPE_CHECKING:
    from dyadpy import App


def snapshot(*, settings: Any = None, manifest: Manifest | None = None) -> dict[str, Any]:
    """Build a serializable snapshot of the running app.

    The shape is stable: the diagnostics page and any third-party tool can
    rely on the keys below. Adding new top-level keys is non-breaking; renaming
    or removing one is.
    """
    return {
        "routes": _route_summary(),
        "tasks": _task_summary(),
        "cron": _cron_summary(),
        "plugins": _plugin_summary(),
        "config": expose_for_client(settings, manifest or Manifest()),
    }


def _route_summary() -> list[dict[str, str]]:
    # The route registry lives on whatever ``App`` the request is being served
    # from. We resolve it lazily through the request context — see ``handler``.
    return []  # filled in at request time; see ``handler`` below


def _task_summary() -> list[dict[str, str | int]]:
    return [
        {
            "name": f"{ref.module}.{ref.name}",
            "queue": ref.queue,
            "retries": ref.retries,
            "backoff": ref.backoff,
        }
        for ref in registered_tasks().values()
    ]


def _cron_summary() -> list[dict[str, str]]:
    return [{"name": f"{ref.module}.{ref.name}", "expr": expr} for ref, expr in cron_jobs()]


def _plugin_summary() -> list[dict[str, str]]:
    return [
        {
            "adapter": type(p).__name__,
            "module": type(p).__module__,
            "contract_version": getattr(p, "contract_version", "?"),
        }
        for p in registered()
    ]


def attach(
    app: App,
    *,
    path: str = "/__quay",
    settings: Any = None,
    manifest: Manifest | None = None,
) -> None:
    """Register the diagnostics handler at ``path`` (default ``/__quay``)."""

    async def handler() -> dict[str, Any]:
        data = snapshot(settings=settings, manifest=manifest)
        # Fill in the route summary from the live App's route table — done at
        # request time so reloads pick up the latest tree.
        data["routes"] = [
            {"method": r.method, "path": r.path, "name": r.name or r.handler.__name__}
            for r in app.routes
        ]
        return data

    app.get(path)(handler)


__all__ = ["attach", "snapshot"]
