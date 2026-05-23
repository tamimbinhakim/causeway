# causeway-db-sqlmodel

SQLModel / SQLAlchemy `DBSession` adapter for Causeway. Auto-loads from `settings.database_url`.

```python
from causeway import register
from causeway_db_sqlmodel import SqlModelSession

register(SqlModelSession(dsn="postgresql+asyncpg://user:pass@host/db"))
```

## Typed JSON columns

Use `json_field()` when a JSON column has a real Python shape and route code
should not deal with `dict[str, Any]`.

```python
from msgspec import Struct
from sqlmodel import SQLModel
from causeway_db_sqlmodel import json_field


class ScreeningSnapshot(Struct):
    score: int
    reasons: list[str]


class Customer(SQLModel, table=True):
    id: int | None = None
    screening: ScreeningSnapshot = json_field(ScreeningSnapshot)
```

The database still stores JSON/JSONB. Values are converted to built-in JSON
types on write and converted back to `ScreeningSnapshot` on read.
