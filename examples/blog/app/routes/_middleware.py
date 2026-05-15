"""App-level middleware: response-time header on every request.

Subtree middleware lives under `(public)/_middleware.py` and
`(admin)/_middleware.py` and composes with this one in outer-to-inner
order on the way in.
"""

from __future__ import annotations

import time

from quay import Middleware
from quay.middleware import CallNext, Request, Response


class TimingHeader(Middleware):
    async def __call__(self, req: Request, call_next: CallNext) -> Response:
        start = time.perf_counter()
        resp = await call_next(req)
        elapsed_ms = (time.perf_counter() - start) * 1000
        resp.headers["x-response-time"] = f"{elapsed_ms:.1f}ms"
        return resp


middleware = [TimingHeader()]
