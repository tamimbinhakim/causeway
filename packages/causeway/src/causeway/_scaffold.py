"""``causeway new`` template tree.

The scaffold ships the smallest viable app: a config file, a plugins file
(empty by default), a lifespan stub, and one route. A user runs ``causeway
dev`` and immediately sees ``GET /`` work.
"""

from __future__ import annotations

from pathlib import Path

_PYPROJECT = """\
[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "causeway>=0.1.0a0",
]

[tool.uv.sources]
causeway = {{ workspace = true }}
"""

_CAUSEWAY_TOML = """\
[app]
name = "{name}"

[client]
# Non-secret settings exposed to the generated TS client.
expose_settings = ["env"]
"""

_ENV_EXAMPLE = """\
ENV=dev
"""

_CONFIG_PY = '''\
"""App settings.

A single :class:`Settings` instance is the source of truth for runtime
config. Pydantic validates it once at import; missing required fields
fail fast with a clear error.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    env: str = "dev"


settings = Settings()
'''

_PLUGINS_PY = '''\
"""Plugin registration.

This module runs once at startup. Use ``causeway.register(...)`` to install
adapters that need constructor arguments (broker URLs, secrets).
Entry-point plugins load automatically — they don't need to be listed here.
"""

from __future__ import annotations
'''

_LIFESPAN_PY = '''\
"""App-level startup / shutdown hooks.

Anything that needs to fire once per process — opening a long-lived
client, warming a cache — goes here. Per-subtree hooks belong in
``routes/<dir>/_scope.py``.
"""

from __future__ import annotations


async def startup() -> None:
    pass


async def shutdown() -> None:
    pass
'''

_MIDDLEWARE_PY = '''\
"""App-level middleware.

Causeway applies these to every route in the tree. Subtree middleware lives
in nested ``_middleware.py`` files.
"""

from __future__ import annotations

middleware: list = []
'''

_INDEX_PY = '''\
"""Root route — ``GET /``."""

from __future__ import annotations

from causeway import get


@get
async def root() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__causeway_test__":
    from causeway.testing import expect, scenario

    with scenario("root responds ok") as it:
        expect(it.get("/")).body == {"status": "ok"}
'''

_EVENT_PY = '''\
"""Example event.

File ``example_created.py`` declares ``class ExampleCreated``, which is
discovered at boot and registered with wire name ``example.created``.
Set ``webhook = True`` to also fan out to ``app/subscribers/``.

Emit from a route or task::

    from app.events.example_created import ExampleCreated
    await ExampleCreated(id="...").emit()

In-process listeners go in ``app/listeners/`` and use ``@ExampleCreated.listen``.
Delete this file once you have your own events.
"""

from __future__ import annotations

from causeway.events import Event


class ExampleCreated(Event):
    id: str
'''


_LISTENER_PY = '''\
"""Example listener for ``ExampleCreated``.

Listener files are imported at boot; the ``@ExampleCreated.listen``
decorator registers ``log_it`` as an in-process reaction. The same listener
file may decorate against multiple events; the same event may be reacted to
from multiple listener files.
"""

from __future__ import annotations

import logging

from app.events.example_created import ExampleCreated


@ExampleCreated.listen
async def log_it(p: ExampleCreated) -> None:
    logging.getLogger("app.listeners").info("example.created %r", p)
'''

_APP_PY = '''\
"""ASGI application entry point.

``causeway dev`` and uvicorn both import ``app:app`` from here. The factory
discovers ``routes/``, registers plugins, and attaches health endpoints.
"""

from __future__ import annotations

from causeway._runtime import App

from causeway.health import attach as attach_health
from causeway.routing import discover, register


def create_app() -> App:
    app = App()
    found = discover("app/routes")
    register(app, found)
    attach_health(app)
    return app


app = create_app()
'''

_TEST_SMOKE_PY = '''\
"""Smoke test — the scaffolded route responds 200."""

from __future__ import annotations

import httpx


async def test_root_responds() -> None:
    from app import app as asgi_app

    transport = httpx.ASGITransport(app=asgi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
'''


_PLUGIN_PYPROJECT = """\
[build-system]
requires = ["hatchling>=1.29.0"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0a0"
description = "TODO"
readme = "README.md"
license = {{ text = "MIT" }}
requires-python = ">=3.11"
dependencies = ["causeway>=0.1.0a0"]

[project.entry-points."causeway.plugins"]
{entry_name} = "{module}:plugin"

[tool.hatch.build.targets.wheel]
packages = ["src/{module}"]
"""

_PLUGIN_INIT = '''\
"""TODO — describe the contract this plugin implements."""

from __future__ import annotations

from typing import Any, ClassVar


class TodoAdapter:
    """Implements :class:`causeway.contracts.TODO`."""

    contract_version: ClassVar[str] = "v1.0"

    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool:
        return True


def plugin(settings: Any) -> None:
    from causeway import register

    register(TodoAdapter())


__all__ = ["TodoAdapter", "plugin"]
'''

_PLUGIN_TEST = '''\
"""Smoke test."""

from __future__ import annotations

from {module} import TodoAdapter


def test_adapter_constructs() -> None:
    assert TodoAdapter()
'''

_PLUGIN_README = """\
# {name}

TODO — describe what this plugin does and how to configure it.
"""


def scaffold_plugin(root: Path, name: str) -> None:
    """Create the package layout for a new plugin under ``root``."""
    module = name.replace("-", "_")
    entry_name = name.removeprefix("causeway-")
    files: dict[str, str] = {
        "pyproject.toml": _PLUGIN_PYPROJECT.format(name=name, module=module, entry_name=entry_name),
        "README.md": _PLUGIN_README.format(name=name),
        f"src/{module}/__init__.py": _PLUGIN_INIT,
        f"tests/test_{module}.py": _PLUGIN_TEST.format(module=module),
    }
    for rel, body in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)


def scaffold(root: Path, name: str) -> None:
    """Materialize the template tree under ``root``."""
    files: dict[str, str] = {
        "pyproject.toml": _PYPROJECT.format(name=name),
        "causeway.toml": _CAUSEWAY_TOML.format(name=name),
        ".env.example": _ENV_EXAMPLE,
        "app/__init__.py": "",
        "app/app.py": _APP_PY,
        "app/config.py": _CONFIG_PY,
        "app/plugins.py": _PLUGINS_PY,
        "app/lifespan.py": _LIFESPAN_PY,
        "app/routes/_middleware.py": _MIDDLEWARE_PY,
        "app/routes/index.py": _INDEX_PY,
        "app/events/example_created.py": _EVENT_PY,
        "app/listeners/log_example.py": _LISTENER_PY,
        "tests/test_smoke.py": _TEST_SMOKE_PY,
    }
    for rel, body in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
