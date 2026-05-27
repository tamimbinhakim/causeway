"""Rich exception panels + ASGI shield that absorbs Starlette's re-raise.

One block per failure: root-caused (unwrap ``ExceptionGroup`` and
``__cause__``/``__context__``), with an operator hint for common
operational errors (Redis/Postgres down, missing module/file). The
shield stops Starlette's ``ServerErrorMiddleware`` re-raise from
reaching the ASGI server so its mega-trace never lands on top of ours.
"""

from __future__ import annotations

import logging
import os
import re
import sysconfig
import traceback
from collections.abc import Awaitable, Callable, MutableMapping
from pathlib import Path
from types import TracebackType
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

_FULL_TRACE_ENV = "CAUSEWAY_FULL_TRACEBACK"
_FRAME_LIMIT_ENV = "CAUSEWAY_TRACEBACK_FRAMES"
_WIDTH_ENV = "CAUSEWAY_TRACEBACK_WIDTH"
_DEFAULT_FRAME_LIMIT = 6
_DEFAULT_PANEL_WIDTH = 100
_MIN_PANEL_WIDTH = 56
_LOG_PREFIX_HEADROOM = 24
_PACKAGE_ROOT = Path(__file__).resolve().parent
_STDLIB = Path(sysconfig.get_paths()["stdlib"]).resolve()
_SITE_PACKAGES = tuple(Path(p).resolve() for p in sysconfig.get_paths().values() if "site" in p)

# Module-level Rich console pointed at stderr. The dev server and any error
# handler share this so output stays in one place (no interleaving with
# uvicorn's own logger writes).
_console: Console = Console(stderr=True, soft_wrap=False, highlight=False)

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def log_exception(
    logger: logging.Logger,
    exc: BaseException,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    message: str = "unhandled exception",
) -> None:
    """Emit a structured logger record AND render a Rich panel to stderr.

    The logger record keeps structured pipelines (JSON, OTLP, caplog tests)
    working; the panel is for the operator watching the dev console. Set
    ``CAUSEWAY_FULL_TRACEBACK=1`` to restore Python's full chained traceback
    via ``logger.exception`` and skip the panel entirely.
    """
    if _full_traceback_enabled():
        logger.exception(message, exc_info=exc)
        return
    root = root_cause(exc)
    logger.error(
        "%s: %s",
        type(root).__name__,
        str(root) or "<no message>",
        extra={
            "event": message,
            "request_id": request_id,
            "exc_type": type(root).__name__,
        },
    )
    render_exception(exc, request=request, request_id=request_id, title=message)


def render_exception(
    exc: BaseException,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    title: str = "unhandled exception",
    console: Console | None = None,
) -> None:
    """Print a comprehensive error panel for ``exc`` to ``console``."""
    target = console or _console
    target.print(
        build_exception_panel(
            exc,
            request=request,
            request_id=request_id,
            title=title,
            width=_panel_width(target),
        )
    )


def build_exception_panel(
    exc: BaseException,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    title: str = "unhandled exception",
    width: int | None = None,
) -> Panel:
    """Compose the Rich ``Panel`` shown for an unhandled exception."""
    root = root_cause(exc)
    sections: list[Any] = []

    header = Text()
    header.append(type(root).__name__, style="bold red")
    header.append("  ")
    header.append(str(root) or "<no message>", style="bold white")
    sections.append(header)

    meta = _meta_block(request, request_id, exc, root)
    if meta is not None:
        sections.append(Text(""))
        sections.append(meta)

    chain = _cause_chain(exc, stop=root)
    if chain:
        sections.append(Text(""))
        sections.append(Text("wrapped by", style="bold dim"))
        for link in chain:
            line = Text("  ")
            line.append(type(link).__name__, style="yellow")
            line.append(": ")
            line.append(str(link) or "<no message>", style="dim")
            sections.append(line)

    frames = _select_frames(
        root.__traceback__ or exc.__traceback__,
        _frame_limit(),
    )
    if frames:
        sections.append(Text(""))
        sections.append(Text("trace", style="bold dim"))
        for frame in frames:
            sections.extend(_frame_block(frame))
    else:
        sections.append(Text(""))
        sections.append(Text("trace: <not available>", style="dim"))

    hint = hint_for(root)
    if hint is not None:
        sections.append(Text(""))
        hint_text = Text()
        hint_text.append("hint  ", style="bold yellow")
        hint_text.append(hint, style="yellow")
        sections.append(hint_text)

    sections.append(Text(""))
    footer = Text(f"full traceback: set {_FULL_TRACE_ENV}=1", style="dim italic")
    sections.append(footer)

    return Panel(
        Group(*sections),
        title=f"[bold red]{title}[/bold red]",
        title_align="left",
        border_style="red",
        padding=(0, 1),
        expand=True,
        width=width,
    )


def _meta_block(
    request: Any | None,
    request_id: str | None,
    exc: BaseException,
    root: BaseException,
) -> Text | None:
    rows: list[tuple[str, str]] = []
    rline = _request_line(request)
    if rline is not None:
        rows.append(("request", rline))
    if request_id is not None:
        rows.append(("request_id", request_id))
    if isinstance(exc, BaseExceptionGroup):
        rows.append(("group", f"{type(exc).__name__} ({len(exc.exceptions)} sub-exception(s))"))
    if root is not exc and root.__cause__ is None and root.__context__ is not None:
        # Hint that the chain came from an implicit context rather than `raise X from Y`.
        rows.append(("via", "implicit __context__"))
    if not rows:
        return None
    width = max(len(label) for label, _ in rows)
    text = Text()
    for i, (label, value) in enumerate(rows):
        if i:
            text.append("\n")
        text.append(f"{label.ljust(width)}  ", style="dim")
        text.append(value, style="white")
    return text


def _frame_block(frame: traceback.FrameSummary) -> list[Any]:
    head = Text("  ")
    head.append(frame.filename, style="cyan")
    head.append(":", style="dim")
    head.append(str(frame.lineno), style="bright_cyan")
    head.append(" in ", style="dim")
    head.append(frame.name, style="bold")
    block: list[Any] = [head]
    if frame.line:
        body = Text("    ")
        body.append(frame.line.strip(), style="white")
        block.append(body)
    return block


def root_cause(exc: BaseException) -> BaseException:
    """Walk ``ExceptionGroup`` + ``__cause__``/``__context__`` to the deepest cause.

    Stops at framework-level wrappers (``BaseHTTPMiddleware``'s task-group
    re-raise) by preferring sub-exceptions over the group itself.
    """
    seen: set[int] = set()
    current: BaseException = exc
    while id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, BaseExceptionGroup):
            subs = list(current.exceptions)
            if subs:
                current = subs[0]
                continue
        nxt: BaseException | None
        if current.__cause__ is not None:
            nxt = current.__cause__
        elif not current.__suppress_context__ and current.__context__ is not None:
            nxt = current.__context__
        else:
            nxt = None
        if nxt is None or id(nxt) in seen:
            break
        current = nxt
    return current


def _cause_chain(exc: BaseException, *, stop: BaseException) -> list[BaseException]:
    """The wrappers between ``exc`` and ``stop`` (exclusive), outermost first.

    Includes ``exc`` itself when it isn't ``stop`` — operators care about
    "what wrapped the real cause," and the outermost wrapper is part of
    that story.
    """
    if exc is stop:
        return []
    chain: list[BaseException] = []
    seen: set[int] = {id(stop)}
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(current)
        if isinstance(current, BaseExceptionGroup):
            subs = list(current.exceptions)
            current = subs[0] if subs else None
            continue
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__ and current.__context__ is not None:
            current = current.__context__
        else:
            current = None
    return [link for link in chain if link is not stop]


def hint_for(exc: BaseException) -> str | None:
    """Operator-friendly hint for common dev errors, or None."""
    name = type(exc).__name__
    msg = str(exc)

    if isinstance(exc, ModuleNotFoundError) and exc.name:
        return (
            f"Module {exc.name!r} is not installed. "
            f"Try `uv add {exc.name}` (or `uv sync` if it's already in pyproject.toml)."
        )
    if isinstance(exc, ImportError):
        target = exc.name or "the import"
        return f"Could not import {target!r}. Check the install and the spelling."
    if isinstance(exc, FileNotFoundError) and exc.filename:
        return f"Path not found: {exc.filename}. Check the path or create the file."
    if isinstance(exc, PermissionError) and exc.filename:
        return f"Permission denied: {exc.filename}. Check filesystem permissions."

    lower = msg.lower()
    connection_signal = (
        "connect call failed" in lower
        or "connection refused" in lower
        or "errno 61" in lower
        or "errno 111" in lower
        or "nodename nor servname" in lower
        or name in {"ConnectionError", "ConnectionRefusedError"}
    )
    if connection_signal:
        if "6379" in msg or "redis" in lower:
            return (
                "Redis is unreachable on :6379. "
                "Start it with `docker compose up -d redis` or set REDIS_URL."
            )
        if "5432" in msg or "postgres" in lower or "psql" in lower:
            return (
                "Postgres is unreachable on :5432. "
                "Start it with `docker compose up -d postgres` or set DATABASE_URL."
            )
        if "27017" in msg or "mongo" in lower:
            return "MongoDB is unreachable on :27017. Start the server or set MONGO_URL."
        host_match = re.search(r"connecting to (\S+)", msg)
        target = host_match.group(1) if host_match else "the dependency"
        return f"Service unreachable ({target}). Is it running?"

    if "timed out" in lower or name.endswith("TimeoutError"):
        return "Operation timed out. The upstream service may be overloaded or unreachable."
    if isinstance(exc, KeyError) and msg.strip("'\""):
        return f"Missing key {msg}. Confirm the data shape or env var is present."

    return None


def _select_frames(tb: TracebackType | None, limit: int) -> list[traceback.FrameSummary]:
    frames = traceback.extract_tb(tb)
    if not frames:
        return []
    user_frames = [frame for frame in frames if not _is_framework_frame(frame.filename)]
    selected = user_frames[-limit:] if user_frames else frames[-limit:]
    return [_relativize_frame(frame) for frame in selected]


def _is_framework_frame(filename: str) -> bool:
    try:
        path = Path(filename).resolve()
    except OSError:
        return False
    if _is_relative_to(path, _PACKAGE_ROOT):
        return True
    if _is_relative_to(path, _STDLIB):
        return True
    return any(_is_relative_to(path, site) for site in _SITE_PACKAGES)


def _relativize_frame(frame: traceback.FrameSummary) -> traceback.FrameSummary:
    filename = frame.filename
    try:
        path = Path(filename).resolve()
        filename = str(path.relative_to(Path.cwd()))
    except (OSError, ValueError):
        pass
    return traceback.FrameSummary(filename, frame.lineno, frame.name, line=frame.line)


def _request_line(request: Any | None) -> str | None:
    if request is None:
        return None
    method = getattr(request, "method", None)
    url = getattr(request, "url", None)
    path = getattr(url, "path", None)
    if isinstance(method, str) and isinstance(path, str):
        return f"{method} {path}"
    return None


def _full_traceback_enabled() -> bool:
    return os.environ.get(_FULL_TRACE_ENV, "").lower() in {"1", "true", "yes", "on"}


def _frame_limit() -> int:
    raw = os.environ.get(_FRAME_LIMIT_ENV)
    if raw is None:
        return _DEFAULT_FRAME_LIMIT
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_FRAME_LIMIT


def _panel_width(console: Console) -> int:
    configured = _configured_panel_width()
    if configured is not None:
        return configured

    columns = max(1, console.size.width)
    if columns <= _MIN_PANEL_WIDTH:
        return columns
    # Many dev processes run under tools that prefix every log line
    # (`api:dev:`, `web:dev:`, etc.). Leaving a little right-side headroom
    # keeps Rich's panel from being wrapped by the outer process, which makes
    # the border look broken.
    prefix_safe = columns - _LOG_PREFIX_HEADROOM
    if prefix_safe < _MIN_PANEL_WIDTH:
        prefix_safe = columns
    return max(_MIN_PANEL_WIDTH, min(_DEFAULT_PANEL_WIDTH, prefix_safe))


def _configured_panel_width() -> int | None:
    raw = os.environ.get(_WIDTH_ENV)
    if raw is None:
        return None
    try:
        return max(_MIN_PANEL_WIDTH, int(raw))
    except ValueError:
        return None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class ExceptionShield:
    """ASGI wrapper that absorbs the re-raise from Starlette's error middleware.

    Starlette's ``ServerErrorMiddleware`` always re-raises after running the
    registered 500 handler (so test clients and outer loggers can see it).
    In a real ASGI server that re-raise turns into a giant unprompted
    traceback printed on top of the compact one our handler already logged.

    This wrapper sits outside the Starlette app and:

    - Lets every successful response through untouched.
    - On an unhandled exception that escapes the app (i.e. the re-raise):
      - If the response has already been sent (the registered handler did
        its job), silently swallow the exception — we've already rendered.
      - Otherwise, write a minimal 500 fallback so the client gets *some*
        response, then swallow.

    The actual error logging is done by the registered handler (e.g.
    ``causeway.errors.error_renderer``), so we don't double-log here.
    """

    __slots__ = ("_fallback_logger", "app")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._fallback_logger = logging.getLogger("causeway.shield")

    def __getattr__(self, name: str) -> object:
        return getattr(self.app, name)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            if not response_started:
                # The registered handler didn't run (or itself raised before
                # writing a response). Render *something* and log here, since
                # nothing else will.
                log_exception(self._fallback_logger, exc)
                await _write_fallback_500(send)
            # Either way, don't let it bubble — the ASGI server would
            # double-log it on top of our pretty render.


async def _write_fallback_500(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"cache-control", b"no-store"),
            ],
        },
    )
    await send(
        {
            "type": "http.response.body",
            "body": b'{"detail":"internal server error"}',
        },
    )


__all__ = [
    "ExceptionShield",
    "build_exception_panel",
    "hint_for",
    "log_exception",
    "render_exception",
    "root_cause",
]
