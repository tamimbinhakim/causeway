# causeway-tasks-dramatiq

Dramatiq adapter for Causeway's `TaskAdapter` contract. Install:

```bash
uv add causeway-tasks-dramatiq
```

Register in `src/app/plugins.py`:

```python
from causeway import register
from causeway_tasks_dramatiq import DramatiqAdapter

register(DramatiqAdapter(broker_url="redis://localhost"))
```

Or let the entry point auto-load and read `settings.redis_url` from your config.
