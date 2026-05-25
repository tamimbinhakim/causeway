"""Compact exception formatting for dev/server diagnostics."""

from __future__ import annotations

import logging
import os
import sysconfig
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any

_FULL_TRACE_ENV = "CAUSEWAY_FULL_TRACEBACK"
_FRAME_LIMIT_ENV = "CAUSEWAY_TRACEBACK_FRAMES"
_DEFAULT_FRAME_LIMIT = 6
_PACKAGE_ROOT = Path(__file__).resolve().parent
_STDLIB = Path(sysconfig.get_paths()["stdlib"]).resolve()
_SITE_PACKAGES = tuple(Path(p).resolve() for p in sysconfig.get_paths().values() if "site" in p)


def log_exception(
    logger: logging.Logger,
    exc: BaseException,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    message: str = "unhandled exception",
) -> None:
    if _full_traceback_enabled():
        logger.exception(message, exc_info=exc)
        return
    logger.error(
        "%s\n%s",
        message,
        format_exception(exc, request=request, request_id=request_id),
    )


def format_exception(
    exc: BaseException,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    max_frames: int | None = None,
) -> str:
    limit = max_frames if max_frames is not None else _frame_limit()
    frames = _select_frames(exc.__traceback__, limit)
    lines = [f"{type(exc).__name__}: {exc or '<no message>'}"]
    request_line = _request_line(request)
    if request_line is not None:
        lines.append(f"request: {request_line}")
    if request_id is not None:
        lines.append(f"request_id: {request_id}")
    if frames:
        lines.append("trace:")
        for frame in frames:
            lines.append(f"  {frame.filename}:{frame.lineno} in {frame.name}")
            if frame.line:
                lines.append(f"    {frame.line.strip()}")
    else:
        lines.append("trace: <not available>")
    lines.append(f"full traceback: set {_FULL_TRACE_ENV}=1")
    return "\n".join(lines)


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


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


__all__ = ["format_exception", "log_exception"]
