# `configure_otel`

Wire OpenTelemetry tracing if the SDK is installed.

```python
from causeway import configure_otel

configure_otel(
    service_name="my-app",
    endpoint="http://otel-collector:4318/v1/traces",
)
```

## Signature

```python
configure_otel(
    *,
    service_name: str = "causeway-app",
    endpoint: str | None = None,
) -> bool
```

## Parameters

| Parameter      | Default              | Notes                                                                        |
| -------------- | -------------------- | ---------------------------------------------------------------------------- |
| `service_name` | `"causeway-app"`     | OTel `service.name` resource attribute.                                      |
| `endpoint`     | `None`               | OTLP/HTTP exporter URL. `None` skips the exporter (spans never leave proc).  |

## Return value

- `True` — instrumentation was attached (the OTel SDK is installed).
- `False` — the OTel SDK isn't installed; the call is a no-op.

```bash
uv add 'causeway[otel]'   # installs the OTel SDK and ASGI instrumentation
```

## Where to call it

In `src/app/lifespan.py`, before the app starts handling requests.

For advanced setups (custom sampling, multiple exporters), build the `TracerProvider` yourself and call `trace.set_tracer_provider(...)` — `configure_otel` is the simple path.

## See also

- [Observability](../../building/observability/index.md)
- [`configure_logging`](./configure-logging.md)
- `instrument_asgi` (in `causeway.observability`) — wraps a raw ASGI app with the OTel ASGI middleware.
