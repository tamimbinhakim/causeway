"""Observability: request-id middleware + structlog setup + OTel hooks.

Quay doesn't pick an exporter — it wires correlation. Each request gets a
request id (read from ``X-Request-Id`` if the caller sent one, otherwise
generated). The id flows onto ``request.state.request_id`` for handlers
and onto structlog's context for every log line. OTel auto-instrumentation
is opt-in; ``configure_otel()`` is a no-op when ``opentelemetry-api`` isn't
installed.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import structlog
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

_log = logging.getLogger("quay.observability")


class RequestIdMiddleware:
    """ASGI middleware that stamps every request with a stable id.

    The id lands on ``request.state.request_id`` (handlers can pull it via
    ``ctx.request.state.request_id``) and on the response as
    ``X-Request-Id``. Downstream services can echo this header to thread
    a single id through a request fan-out.
    """

    HEADER = "x-request-id"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []) or [])
        existing = headers.get(self.HEADER.encode())
        request_id = existing.decode() if existing else uuid.uuid4().hex
        scope.setdefault("state", {})  # type: ignore[typeddict-item]
        scope["state"]["request_id"] = request_id  # type: ignore[typeddict-item]

        async def send_with_header(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                raw_headers.append((self.HEADER.encode(), request_id.encode()))
                message["headers"] = raw_headers
            await send(message)

        # Bind into structlog context for the duration of this request.
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            await self.app(scope, receive, send_with_header)


def configure_logging(*, level: str = "INFO", json: bool = True) -> None:
    """Set up structlog so every log line is structured and correlated.

    Pass ``json=False`` for a pretty console renderer in dev. Production runs
    keep ``json=True`` so a log shipper can ingest the lines directly.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    pre_chain = [
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


def configure_otel(*, service_name: str = "quay-app", endpoint: str | None = None) -> bool:
    """Wire OTel auto-instrumentation if the dependencies are available.

    Returns ``True`` when instrumentation was attached, ``False`` when the
    OTel SDK isn't installed (Quay's ``otel`` extra). Quay doesn't ship the
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
    "request_id_of",
]
