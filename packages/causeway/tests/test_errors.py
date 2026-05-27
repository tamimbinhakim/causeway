"""Error rendering tests."""

from __future__ import annotations

import json

from starlette.requests import Request

from causeway._runtime.errors import exception_to_payload
from causeway.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    HttpError,
    NotFound,
    Unauthorized,
    format_http_error,
    render_problem,
)


def _body(resp) -> dict:
    return json.loads(resp.body.decode())


def test_renders_known_http_error() -> None:
    resp = render_problem(NotFound("user 42 missing"))
    assert resp.status_code == 404
    assert resp.media_type == "application/problem+json"
    body = _body(resp)
    assert body["status"] == 404
    assert body["title"] == "not_found"
    assert body["detail"] == "user 42 missing"


def test_renders_with_request_id() -> None:
    resp = render_problem(Conflict("dup"), request_id="r-123")
    body = _body(resp)
    assert body["request_id"] == "r-123"


def test_renders_permission_error_as_403() -> None:
    resp = render_problem(PermissionError("nope"))
    assert resp.status_code == 403
    assert _body(resp)["title"] == "forbidden"


def test_renders_lookup_error_as_404() -> None:
    resp = render_problem(KeyError("user 7"))
    assert resp.status_code == 404


def test_unknown_exception_becomes_generic_500() -> None:
    resp = render_problem(RuntimeError("internal database failure"))
    assert resp.status_code == 500
    body = _body(resp)
    # Don't leak the internal message.
    assert "database" not in body["detail"]


def test_http_error_subclass_codes() -> None:
    assert BadRequest().status == 400
    assert Unauthorized().status == 401
    assert Forbidden().status == 403
    assert Conflict().status == 409


def test_http_error_carries_params() -> None:
    err = HttpError("bad", detail={"field": "email", "reason": "invalid"})
    resp = render_problem(err)
    body = _body(resp)
    assert body["params"] == {"field": "email", "reason": "invalid"}


def test_http_error_default_payload_matches_problem_shape() -> None:
    payload = format_http_error(BadRequest("bad", detail={"field": "email"}))

    assert payload == {
        "status": 400,
        "code": "bad_request",
        "message": "bad",
        "detail": {"field": "email"},
    }


def test_http_error_formatter_customizes_problem_and_result_payloads() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/x", "headers": []})

    def formatter(exc: HttpError, req: Request | None) -> dict[str, object]:
        assert req is request
        return {
            "message": f"Friendly: {exc.message}",
            "detail": {"path": req.url.path if req is not None else ""},
        }

    problem = _body(
        render_problem(BadRequest("raw_code"), request=request, error_formatter=formatter),
    )
    result_payload = exception_to_payload(
        BadRequest("raw_code"),
        request=request,
        error_formatter=formatter,
    )

    assert problem["detail"] == "Friendly: raw_code"
    assert problem["params"] == {"path": "/x"}
    assert result_payload["message"] == "Friendly: raw_code"
    assert result_payload["detail"] == {"path": "/x"}
