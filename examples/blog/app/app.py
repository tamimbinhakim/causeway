"""ASGI entry point.

Importing `app.plugins` registers the in-process task adapter so the
plugin registry sees it before `create_app` builds the lifespan. The
root `routes/_scope.py` then fires plugin + lifespan startup hooks.
"""

from __future__ import annotations

import app.plugins  # noqa: F401  # side-effect: register adapters
from quay import create_app

app = create_app("app/routes")
