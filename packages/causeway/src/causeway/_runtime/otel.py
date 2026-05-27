"""OpenTelemetry middleware — opt-in tracing for Dyadpy apps.

Lazy-import OpenTelemetry so apps that don't use it pay zero cost. Wraps
the ASGI app and emits one span per request with the route name, method,
path, and outcome.

Wire into your app::

    from causeway._runtime import App
    from causeway._runtime.otel import instrument

    app = instrument(App())

Or — if you want fuller control — pass a tracer provider you've configured
yourself.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def instrument(app: ASGIApp) -> ASGIApp:
    """Wrap an ASGI app with an OTel tracing span per request.

    No-op if ``opentelemetry-api`` isn't installed — you'll get back the
    original app unchanged.
    """
    try:
        from opentelemetry import trace
    except ImportError:
        return app

    tracer = trace.get_tracer("dyadpy")

    async def wrapped(scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            return await app(scope, receive, send)
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        with tracer.start_as_current_span(f"{method} {path}") as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.target", path)
            status_seen: dict[str, int] = {"code": 0}

            async def send_wrapper(message: Message) -> None:
                if message.get("type") == "http.response.start":
                    status_seen["code"] = int(message.get("status", 0))
                    span.set_attribute("http.status_code", status_seen["code"])
                await send(message)

            try:
                await app(scope, receive, send_wrapper)
            except Exception:
                span.set_attribute("error", True)
                raise

    return wrapped
