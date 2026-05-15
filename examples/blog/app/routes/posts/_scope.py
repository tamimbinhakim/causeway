"""Per-request DB session for everything under `/posts`."""

from __future__ import annotations

from app.deps import db_session  # noqa: F401  # discovered by name
