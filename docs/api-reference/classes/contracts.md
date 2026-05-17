# Plugin contracts

Every plugin contract in `causeway.contracts`. All are `typing.Protocol`s — duck-typed, no inheritance required.

```python
from causeway.contracts import (
    Plugin,
    TaskAdapter,
    Storage,
    KV,
    SessionStore,
    Mailer,
    PubSub,
    RateLimiter,
    FeatureFlags,
    MetricsSink,
    LogSink,
    Searchable,
    DBSession,
    AuthProvider,
    BlobScanner,
    DeployTarget,
)
```

Every contract carries a `contract_version: ClassVar[str] = "v1.0"` so the registry can warn when a plugin targets an older protocol.

---

## `Plugin` (base)

Every contract inherits this.

```python
class Plugin(Protocol):
    contract_version: ClassVar[str]
    async def startup(self, settings: Any) -> None: ...
    async def shutdown(self) -> None: ...
    async def ready(self) -> bool: ...
```

---

## `TaskAdapter`

```python
class TaskAdapter(Plugin, Protocol):
    async def enqueue(self, task: TaskRef, payload: bytes) -> str: ...
    async def schedule(self, task: TaskRef, when: datetime, payload: bytes) -> str: ...
    async def cron(self, task: TaskRef, expr: str) -> None: ...
    def eager(self) -> AsyncContextManager[None]: ...
    async def status(self, task_id: str) -> TaskStatus: ...
    async def result(self, task_id: str) -> Any: ...
```

Reference: `causeway.tasks.InMemoryAdapter`. Real adapters: `causeway-tasks-dramatiq`.

---

## `Storage`

```python
class Storage(Plugin, Protocol):
    async def put(self, key: str, body: bytes, *, content_type: str | None = None) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def signed_url(self, key: str, *, expires: int = 3600) -> str: ...
    async def list(self, prefix: str = "") -> AsyncIterator[str]: ...
```

Reference: `causeway.adapters.LocalStorage`. Real adapters: `causeway-storage-fs`, `causeway-storage-s3`.

---

## `KV`

```python
class KV(Plugin, Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, *, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def incr(self, key: str, by: int = 1) -> int: ...
    async def expire(self, key: str, ttl: int) -> None: ...
```

Reference: `causeway.adapters.MemoryKV`. Real adapters: `causeway-cache-redis`.

---

## `SessionStore`

```python
class SessionStore(Plugin, Protocol):
    async def read(self, session_id: str) -> dict[str, Any] | None: ...
    async def write(self, session_id: str, data: dict[str, Any]) -> None: ...
    async def destroy(self, session_id: str) -> None: ...
    async def rotate(self, session_id: str) -> str: ...
```

Reference: `causeway.adapters.CookieStore`.

---

## `Mailer`

```python
class Mailer(Plugin, Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
    async def send_template(self, to: str, template: str, data: dict[str, Any]) -> None: ...
    async def verify_address(self, address: str) -> bool: ...
```

Real adapters: `causeway-mailer-smtp`. No in-core reference.

---

## `PubSub`

```python
class PubSub(Plugin, Protocol):
    async def publish(self, topic: str, payload: bytes) -> None: ...
    async def subscribe(self, topic: str, handler: Callable[[bytes], Awaitable[None]]) -> None: ...
```

---

## `RateLimiter`

```python
class RateLimiter(Plugin, Protocol):
    async def acquire(self, key: str, cost: int = 1) -> bool: ...
    async def peek(self, key: str) -> int: ...
    async def reset(self, key: str) -> None: ...
```

Reference: `causeway.adapters.MemoryLimiter` (token bucket).

---

## `FeatureFlags`

```python
class FeatureFlags(Plugin, Protocol):
    async def is_on(self, flag: str, user: str | None = None) -> bool: ...
    async def variant(self, flag: str, user: str | None = None) -> str | None: ...
    async def refresh(self) -> None: ...
```

Reference: `causeway.adapters.StaticFlags` (reads `Settings.feature_flags`). Real adapters: `causeway-flags-growthbook`.

---

## `MetricsSink`

```python
class MetricsSink(Plugin, Protocol):
    def counter(self, name: str, value: float = 1.0, **tags: str) -> None: ...
    def gauge(self, name: str, value: float, **tags: str) -> None: ...
    def histogram(self, name: str, value: float, **tags: str) -> None: ...
    def timer(self, name: str, **tags: str) -> AsyncContextManager[None]: ...
```

---

## `LogSink`

```python
class LogSink(Plugin, Protocol):
    def emit(self, record: dict[str, Any]) -> None: ...
```

Reference: stdout via `structlog`.

---

## `Searchable`

```python
class Searchable(Plugin, Protocol):
    async def index(self, doc_id: str, doc: dict[str, Any]) -> None: ...
    async def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]: ...
    async def delete(self, doc_id: str) -> None: ...
    async def bulk_index(self, docs: list[tuple[str, dict[str, Any]]]) -> None: ...
```

---

## `DBSession`

```python
class DBSession(Plugin, Protocol):
    def session(self) -> AsyncContextManager[Any]: ...
    def transaction(self) -> AsyncContextManager[Any]: ...
    async def health(self) -> bool: ...
```

Real adapters: `causeway-db-sqlmodel`.

---

## `AuthProvider`

```python
class AuthProvider(Plugin, Protocol):
    async def current_user(self, req: Any) -> Any | None: ...
    async def login(self, creds: dict[str, Any]) -> Any: ...
    async def logout(self, req: Any) -> None: ...
    async def verify(self, token: str) -> Any | None: ...
```

Real adapters: `causeway-auth-jwt`.

---

## `BlobScanner`

```python
class BlobScanner(Plugin, Protocol):
    async def scan(self, stream: AsyncIterator[bytes]) -> bool: ...
```

---

## `DeployTarget`

```python
class DeployTarget(Plugin, Protocol):
    def manifest(self) -> dict[str, Any]: ...
    def package(self) -> bytes: ...
    async def push(self, target: str) -> str: ...
```

Real adapters: `causeway-deploy-docker`, `causeway-deploy-fly`, `causeway-deploy-modal`.

---

## Contract versioning

Each contract carries `contract_version: ClassVar[str]`. The registry warns when a plugin targets a version other than the loaded one.

After 1.0:

- Adding optional methods → non-breaking.
- Removing or renaming a method → breaking; follows the deprecation cycle in [`semver`](../../stability/semver.md).

## See also

- [Plugins overview](../../building/plugins/index.md)
- [Writing a plugin](../../building/plugins/authoring.md)
- [`register`](../functions/register.md)
