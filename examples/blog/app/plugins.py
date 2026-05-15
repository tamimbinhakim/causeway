"""Plugin registration.

Entry-point plugins (anything installed via pip with a `causeway.plugins`
entry point) load automatically. Adapters that need constructor args
go here — they're installed by calling `causeway.register(...)`.

For this example we register the in-process task adapter so `@task`
and `@cron` actually run. Importing `app.tasks` is enough to register
the task definitions themselves.
"""

from __future__ import annotations

from causeway import register
from causeway.tasks import InMemoryAdapter

# Import so @task / @cron decorators run and register their refs.
import app.tasks  # noqa: F401

register(InMemoryAdapter())
