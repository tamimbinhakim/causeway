# quay-tasks-dramatiq

Dramatiq adapter for Quay's `TaskAdapter` contract. Install:

```bash
uv add quay-tasks-dramatiq
```

Register in `src/app/plugins.py`:

```python
from quay import register
from quay_tasks_dramatiq import DramatiqAdapter

register(DramatiqAdapter(broker_url="redis://localhost"))
```

Or let the entry point auto-load and read `settings.redis_url` from your config.
