"""Quay — a lean backend framework on top of Dyadpy.

This is the structural boilerplate for the package. Implementation lands
incrementally per the v0.1 roadmap; see ROADMAP.md.

Public API surface (to be populated):

- Method decorators: ``get``, ``post``, ``put``, ``patch``, ``delete``
- Routing helpers: ``Middleware``, ``guard``, ``provide``
- Errors: ``raises`` (re-exported from dyadpy), ``quay.errors`` namespace
- Background tasks: ``task``, ``cron``
- Plugin registry: ``register``
- Testing: ``TestApp``
"""

__version__ = "0.1.0a0"

__all__ = ["__version__"]
