"""ASGI entry point.

`create_app` loads sibling `plugins.py` and `lifespan.py`, then owns their
startup/shutdown lifecycle.
"""

from __future__ import annotations

from causeway import create_app

app = create_app("app/routes")
