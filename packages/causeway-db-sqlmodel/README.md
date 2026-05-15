# causeway-db-sqlmodel

SQLModel / SQLAlchemy `DBSession` adapter for Causeway. Auto-loads from `settings.database_url`.

```python
from causeway import register
from causeway_db_sqlmodel import SqlModelSession

register(SqlModelSession(dsn="postgresql+asyncpg://user:pass@host/db"))
```
