"""ASGI entry point."""

from __future__ import annotations

from quay import create_app

app = create_app("app/routes")
