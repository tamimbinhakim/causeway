"""Plugin registration.

Entry-point plugins (anything installed via pip with a `quay.plugins`
entry point) load automatically. Adapters that need constructor args
go here — they're installed by calling `quay.register(...)`.

For this example we register the in-process task adapter so `@task`
and `@cron` actually run. Importing `app.tasks` is enough to register
the task definitions themselves.
"""

from __future__ import annotations

from quay import register
from quay.tasks import InMemoryAdapter

# Import so @task / @cron decorators run and register their refs.
import app.tasks  # noqa: F401

register(InMemoryAdapter())
