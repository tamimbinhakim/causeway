"""Observability: request-id middleware, structlog setup, OTel hooks.

Causeway wires correlation; the exporter is the user's choice. OTel setup is
a no-op when the SDK isn't installed. ``structlog`` is loaded lazily so
``import causeway`` doesn't pay its ~16ms import cost when the caller
never configures structured logging.
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_log = logging.getLogger("causeway.observability")


def _structlog_bind(request_id: str) -> Any:
    """Return the structlog request-id context manager if structlog is loaded,
    otherwise a no-op. Detected by ``sys.modules`` lookup so users who
    import structlog themselves still get correlation without calling
    ``configure_logging``.
    """
    mod = sys.modules.get("structlog")
    if mod is None:
        return _NoopBind
    return mod.contextvars.bound_contextvars(request_id=request_id)


class _NoopBindClass:
    def __enter__(self) -> None: ...
    def __exit__(self, *exc: object) -> None: ...


_NoopBind = _NoopBindClass()


class RequestIdMiddleware:
    """ASGI middleware that stamps every request with a stable id.

    The id lands on ``request.state.request_id`` (handlers can pull it via
    ``ctx.request.state.request_id``) and on the response as
    ``X-Request-Id``. Downstream services can echo this header to thread
    a single id through a request fan-out.
    """

    HEADER = b"x-request-id"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        existing: bytes | None = None
        for name, value in scope.get("headers", ()) or ():
            if name == self.HEADER:
                existing = value
                break
        request_id = existing.decode() if existing else uuid.uuid4().hex
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        header_pair = (self.HEADER, request_id.encode())

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", ()), header_pair]
            await send(message)

        with _structlog_bind(request_id):
            await self.app(scope, receive, send_with_header)


def configure_logging(*, level: str = "INFO", json: bool = True) -> None:
    """Set up structlog so every log line is structured and correlated.

    Pass ``json=False`` for a pretty console renderer in dev. Production runs
    keep ``json=True`` so a log shipper can ingest the lines directly.
    """
    # Deferred so ``import causeway`` doesn't pay structlog's import cost
    # for apps that never configure structured logging.
    import structlog

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    pre_chain: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        timestamper,
    ]
    renderer = structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[*pre_chain, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(_log_level(level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _log_level(name: str) -> int:
    return getattr(logging, name.upper(), logging.INFO)


def configure_otel(*, service_name: str = "causeway-app", endpoint: str | None = None) -> bool:
    """Wire OTel auto-instrumentation if the dependencies are available.

    Returns ``True`` when instrumentation was attached, ``False`` when the
    OTel SDK isn't installed (Causeway's ``otel`` extra). Causeway doesn't ship the
    exporter selection — let the user pick OTLP / SigNoz / Honeycomb via env.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        _log.debug("opentelemetry-api not installed; skipping OTel setup")
        return False

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        except ImportError:
            _log.warning("OTLP exporter not installed; spans will not export")
    trace.set_tracer_provider(provider)
    return True


def instrument_asgi(app: Any) -> Any:
    """Wrap an ASGI app with OpenTelemetry's ASGI instrumentation if installed.

    Returns the wrapped app on success or the original ``app`` unchanged
    when ``opentelemetry-instrumentation-asgi`` isn't installed.
    """
    try:
        from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
    except ImportError:
        _log.debug("opentelemetry-instrumentation-asgi not installed; skipping wrap")
        return app
    return OpenTelemetryMiddleware(app)


def request_id_of(request: Request | None) -> str | None:
    """Read the request id off a Starlette Request, if one was stamped."""
    if request is None:
        return None
    return getattr(request.state, "request_id", None)


__all__ = [
    "RequestIdMiddleware",
    "Response",
    "configure_logging",
    "configure_otel",
    "instrument_asgi",
    "request_id_of",
]
