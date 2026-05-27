"""IR → OpenAPI 3.1 export.

For users who also need to serve external (non-causeway) clients — generate
a standard OpenAPI 3.1 document from the same IR the TS codegen consumes.
We don't ship Swagger UI; that's a separate concern.

Mapping notes:

- Each ``RouteIR`` becomes a ``paths[path][method]`` entry.
- ``response`` schema → 200 response. ``raises`` errors → 4xx responses
  keyed by error name (status 422 by default; users can override post-hoc).
- Streaming endpoints document ``text/event-stream`` as the response
  content type with the event schema in ``application/json`` for tooling.
- Shared components land under ``components.schemas`` reusing the same
  names the TS codegen settled on.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from causeway._runtime.ir import AppIR, RouteIR


def render(ir: AppIR, *, title: str = "Causeway API", version: str = "0.0.0") -> dict[str, Any]:
    paths: dict[str, dict[str, Any]] = {}
    for route in ir.routes:
        method_obj = _render_route(route)
        paths.setdefault(route.path, {})[route.method.lower()] = method_obj

    return {
        "openapi": "3.1.0",
        "info": {"title": title, "version": version},
        "paths": paths,
        "components": {"schemas": ir.components},
    }


def write(ir: AppIR, out: Path, *, title: str = "Causeway API", version: str = "0.0.0") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(render(ir, title=title, version=version), indent=2), encoding="utf-8")


def _render_route(route: RouteIR) -> dict[str, Any]:
    parameters: list[dict[str, Any]] = []
    request_body: dict[str, Any] | None = None
    body_props: dict[str, dict[str, Any]] = {}
    body_required: list[str] = []
    file_props: dict[str, dict[str, Any]] = {}

    for p in route.params:
        if p.location in ("path", "query", "header", "cookie"):
            parameters.append(
                {
                    "name": p.alias,
                    "in": p.location,
                    "required": p.required if p.location != "path" else True,
                    "schema": p.schema,
                }
            )
        elif p.location == "body":
            if p.embed:
                body_props[p.alias] = p.schema
                if p.required:
                    body_required.append(p.alias)
            else:
                request_body = {
                    "required": p.required,
                    "content": {"application/json": {"schema": p.schema}},
                }
        elif p.location == "file":
            file_props[p.alias] = {"type": "string", "format": "binary"}

    if body_props and request_body is None:
        request_body = {
            "required": bool(body_required),
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": body_props,
                        "required": body_required,
                    }
                }
            },
        }

    if file_props:
        request_body = {
            "required": True,
            "content": {
                "multipart/form-data": {"schema": {"type": "object", "properties": file_props}}
            },
        }

    responses: dict[str, Any] = {}
    if route.streams:
        event_schema = route.event_schema or {}
        responses["200"] = {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {"schema": event_schema}},
        }
    else:
        responses["200"] = {
            "description": "OK",
            "content": {"application/json": {"schema": route.response or {}}},
        }

    for err in route.raises:
        responses["422"] = {
            "description": err.name,
            "content": {"application/json": {"schema": err.schema}},
        }

    obj: dict[str, Any] = {"operationId": route.name, "responses": responses}
    if parameters:
        obj["parameters"] = parameters
    if request_body is not None:
        obj["requestBody"] = request_body
    return obj
