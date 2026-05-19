"""Batch endpoints — per-item success/failure responses with HTTP 207.

The framework's stance: bulk endpoints with mixed outcomes are common enough
that every team should reuse one shape rather than inventing their own. The
shape is ``{ok: list[T], failed: list[{input, error}]}``; the status code is
207 when anything failed and 200 when everything succeeded.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Generic, TypeVar

import msgspec

from causeway.errors import HttpError

T = TypeVar("T")
E = TypeVar("E", bound=HttpError)


class BatchFailure(msgspec.Struct, Generic[T, E]):
    """One item that failed in a batch.

    ``input`` carries the original payload so clients can correlate the
    failure back to the request item; ``error`` is the typed error itself.
    """

    input: T
    error: E


class BatchResult(msgspec.Struct, Generic[T, E]):
    """Per-item outcomes for a bulk endpoint.

    Construct empty, then append to ``ok`` / ``failed`` as you process items.
    The ``@batch`` decorator inspects this on the way out to set 207 vs 200.
    """

    ok: list[T] = msgspec.field(default_factory=list)
    failed: list[BatchFailure[T, E]] = msgspec.field(default_factory=list)


def batch(handler: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a handler as a batch endpoint.

    Sets the response status to 207 Multi-Status when the returned
    :class:`BatchResult` has any failures, 200 otherwise. The handler runs
    the per-item loop and appends to ``ok`` / ``failed`` itself — the
    decorator does not catch exceptions on its behalf.

    See ``docs/building/handlers/batch.md`` for the canonical shape.
    """
    wrapper: Callable[..., Any]
    if iscoroutinefunction(handler):

        @wraps(handler)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await handler(*args, **kwargs)
            _apply_status(result)
            return result

        wrapper = async_wrapper
    else:

        @wraps(handler)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = handler(*args, **kwargs)
            _apply_status(result)
            return result

        wrapper = sync_wrapper

    wrapper.__causeway_batch__ = True  # type: ignore[union-attr]
    return wrapper


def _apply_status(result: Any) -> None:
    if not isinstance(result, BatchResult):
        return
    # The context var is set by dyadpy's runtime around each handler invocation;
    # outside that loop (e.g. direct call from tests) there's nothing to mutate.
    from dyadpy.context import current_context_var

    try:
        ctx = current_context_var.get()
    except LookupError:
        return
    ctx.response_status = 207 if result.failed else 200


def is_batch(handler: Any) -> bool:
    return bool(getattr(handler, "__causeway_batch__", False))


__all__ = ["BatchFailure", "BatchResult", "batch", "is_batch"]
