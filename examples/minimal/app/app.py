"""ASGI entry point. Run with `uv run uvicorn app.app:app --reload`."""

from __future__ import annotations

from causeway import create_app

app = create_app("app/routes")
