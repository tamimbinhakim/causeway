# quay-sqlmodel

SQLModel / SQLAlchemy `DBSession` adapter for Quay. Auto-loads from `settings.database_url`.

```python
from quay import register
from quay_sqlmodel import SqlModelSession

register(SqlModelSession(dsn="postgresql+asyncpg://user:pass@host/db"))
```
