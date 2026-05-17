"""Tests for the batch endpoint primitive."""

from __future__ import annotations

import msgspec
import pytest

from causeway.batch import BatchFailure, BatchResult, batch, is_batch
from causeway.errors import BadRequest


class _Item(msgspec.Struct):
    name: str


def test_batch_marks_handler() -> None:
    @batch
    async def handler() -> BatchResult[_Item, BadRequest]:
        return BatchResult()

    assert is_batch(handler)


@pytest.mark.asyncio
async def test_batch_sets_207_on_failure() -> None:
    from dyadpy.context import Context, current_context_var
    from starlette.requests import Request

    @batch
    async def handler() -> BatchResult[_Item, BadRequest]:
        out: BatchResult[_Item, BadRequest] = BatchResult()
        out.ok.append(_Item(name="a"))
        out.failed.append(
            BatchFailure[_Item, BadRequest](input=_Item(name="b"), error=BadRequest("nope")),
        )
        return out

    req = Request({"type": "http", "headers": [], "method": "POST", "path": "/"})
    ctx = Context(request=req)
    token = current_context_var.set(ctx)
    try:
        await handler()
    finally:
        current_context_var.reset(token)
    assert ctx.response_status == 207


@pytest.mark.asyncio
async def test_batch_sets_200_when_all_succeed() -> None:
    from dyadpy.context import Context, current_context_var
    from starlette.requests import Request

    @batch
    async def handler() -> BatchResult[_Item, BadRequest]:
        out: BatchResult[_Item, BadRequest] = BatchResult()
        out.ok.append(_Item(name="a"))
        return out

    req = Request({"type": "http", "headers": [], "method": "POST", "path": "/"})
    ctx = Context(request=req)
    token = current_context_var.set(ctx)
    try:
        await handler()
    finally:
        current_context_var.reset(token)
    assert ctx.response_status == 200


@pytest.mark.asyncio
async def test_batch_handles_empty_input() -> None:
    from dyadpy.context import Context, current_context_var
    from starlette.requests import Request

    @batch
    async def handler() -> BatchResult[_Item, BadRequest]:
        return BatchResult()

    req = Request({"type": "http", "headers": [], "method": "POST", "path": "/"})
    ctx = Context(request=req)
    token = current_context_var.set(ctx)
    try:
        result = await handler()
    finally:
        current_context_var.reset(token)
    assert ctx.response_status == 200
    assert result.ok == []
    assert result.failed == []


def test_batch_result_serializes_cleanly() -> None:
    out: BatchResult[_Item, BadRequest] = BatchResult()
    out.ok.append(_Item(name="a"))
    out.failed.append(
        BatchFailure[_Item, BadRequest](input=_Item(name="b"), error=BadRequest("oops")),
    )
    # msgspec can't directly encode HttpError (Exception subclass); the IR
    # builder synthesizes a tagged Struct for it. Here we only check the
    # successful-side serializes.
    encoded = msgspec.json.encode(out.ok)
    assert msgspec.json.decode(encoded) == [{"name": "a"}]
