"""Quay — a lean backend framework for type-safe Python APIs.

This is the structural boilerplate for the package. Implementation lands
incrementally per the v0.1 roadmap; see ROADMAP.md.

Public API surface (to be populated):

- Method decorators: ``get``, ``post``, ``put``, ``patch``, ``delete``
- Routing helpers: ``Middleware``, ``guard``, ``provide``
- Errors: ``raises``, ``quay.errors`` namespace
- Streaming: ``stream``
- Background tasks: ``task``, ``cron``
- Plugin registry: ``register``
- Testing: ``TestApp``
"""

__version__ = "0.1.0a0"

__all__ = ["__version__"]
