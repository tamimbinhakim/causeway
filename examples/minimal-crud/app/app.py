"""ASGI entry point."""

from __future__ import annotations

from causeway import create_app

app = create_app("app/routes")
