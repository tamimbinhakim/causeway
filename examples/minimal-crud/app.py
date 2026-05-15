"""Minimal CRUD example.

Demonstrates: file-based routing, scoped DI, typed errors, an in-memory
store wired through the plugin registry. The handlers themselves are
ordinary async functions — Quay's job is to make the project shape
trivial; the business logic is yours.
"""

from __future__ import annotations

from dyadpy import App

from quay.health import attach as attach_health
from quay.routing import discover, register


def create_app() -> App:
    app = App()
    register(app, discover("routes"))
    attach_health(app)
    return app


app = create_app()
