from __future__ import annotations

import atexit
import json
import threading
from typing import Any
from typing import Literal

from fastmcp import Context
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.apps import AppConfig
from fastmcp.server.apps import ResourceCSP

import panel_live_server.server as panel_server

from models import SUPPORTED_PLOT_TYPES
from state import create_plot_record, update_plot_record
from viz import build_visualization_code


mcp = FastMCP(
    "HoloViz Panel MCP",
    instructions=(
        "Use the structured plotting tools first when the user wants a simple "
        "scatter, line, or bar chart from tabular JSON data. These tools return "
        "an MCP App payload for inline rendering when the client supports it."
    ),
)

_RENDERER_LOCK = threading.Lock()
_WARMUP_STARTED = False


def _tool_name(plot_type: str, plot_id: str, version: int) -> str:
    return f"{plot_type.title()} Plot {plot_id} v{version}"


def _tool_description(x: str, y: str) -> str:
    return f"Interactive visualization of `{y}` against `{x}`."


def _ensure_renderer_ready() -> None:
    with _RENDERER_LOCK:
        if panel_server._client and panel_server._client.is_healthy():
            return

        manager, client = panel_server._start_panel_server()
        if not manager or not client:
            raise RuntimeError("Failed to start panel-live-server renderer.")

        panel_server._manager = manager
        panel_server._client = client


def _warm_renderer_background() -> None:
    global _WARMUP_STARTED

    if _WARMUP_STARTED:
        return

    _WARMUP_STARTED = True

    def _runner() -> None:
        try:
            _ensure_renderer_ready()
        except Exception:
            # Best-effort warmup only. Tool calls will retry on demand.
            return

    threading.Thread(target=_runner, daemon=True, name="panel-renderer-warmup").start()


atexit.register(panel_server._cleanup)
_warm_renderer_background()


@mcp.resource(
    panel_server.SHOW_RESOURCE_URI,
    app=AppConfig(
        csp=ResourceCSP(
            resource_domains=["'unsafe-inline'", "https://unpkg.com"],
            frame_domains=panel_server._build_frame_domains(),
        )
    ),
)
def show_view() -> str:
    return panel_server.show_view()


async def _render_record(record) -> str:
    _ensure_renderer_ready()
    code = build_visualization_code(record.request)
    response = panel_server._client.create_snippet(
        code=code,
        name=_tool_name(record.request.plot_type, record.plot_id, record.version),
        description=_tool_description(record.request.x, record.request.y),
        method="jupyter",
    )

    if error_message := response.get("error_message"):
        raise ToolError(
            "Visualization was created but failed at runtime:\n"
            f"{error_message}\n"
            "Fix the generated chart code path and try again."
        )

    payload = {
        "tool": "show",
        "name": _tool_name(record.request.plot_type, record.plot_id, record.version),
        "description": _tool_description(record.request.x, record.request.y),
        "method": "jupyter",
        "zoom": 100,
        "url": response["url"],
        "code": code,
        "status": "success",
        "message": "Visualization created successfully.",
    }
    payload["plot_id"] = record.plot_id
    payload["version"] = record.version
    payload["plot_type"] = record.request.plot_type
    return json.dumps(payload)


@mcp.tool(
    name="create_plot",
    description="Create a schema-validated HoloViews plot and render it inline via panel-live-server.",
    app=AppConfig(resource_uri=panel_server.SHOW_RESOURCE_URI),
)
async def create_plot(
    data: list[dict[str, Any]],
    plot_type: str,
    x: str,
    y: str,
) -> str:
    record = create_plot_record(data=data, plot_type=plot_type, x=x, y=y)
    return await _render_record(record)


@mcp.tool(
    name="update_plot",
    description="Update a schema-validated plot and render the new version inline via panel-live-server.",
    app=AppConfig(resource_uri=panel_server.SHOW_RESOURCE_URI),
)
async def update_plot(
    plot_id: str,
    data: list[dict[str, Any]] | None = None,
    plot_type: str | None = None,
    x: str | None = None,
    y: str | None = None,
) -> str:
    record = update_plot_record(
        plot_id,
        data=data,
        plot_type=plot_type,
        x=x,
        y=y,
    )
    return await _render_record(record)


@mcp.tool(description="List the plot types supported by the structured plotting layer.")
def list_plot_types() -> list[str]:
    return SUPPORTED_PLOT_TYPES


@mcp.tool(name="list_packages")
async def list_packages(
    category: str = "core",
    query: str = "",
    include_versions: bool = False,
    ctx: Context | None = None,
) -> list[str] | list[dict[str, str]]:
    return await panel_server.list_packages(
        category=category,
        query=query,
        include_versions=include_versions,
        ctx=ctx,
    )


@mcp.tool(name="validate")
async def validate(
    code: str,
    method: Literal["jupyter", "panel"] = "jupyter",
    ctx: Context | None = None,
) -> dict:
    return await panel_server.validate(code=code, method=method, ctx=ctx)


@mcp.tool(name="show", app=AppConfig(resource_uri=panel_server.SHOW_RESOURCE_URI))
async def show(
    code: str,
    name: str = "",
    description: str = "",
    method: Literal["jupyter", "panel"] = "jupyter",
    zoom: int = 100,
    quick: bool = False,
    ctx: Context | None = None,
) -> str:
    _ensure_renderer_ready()
    return await panel_server.show(
        code=code,
        name=name,
        description=description,
        method=method,
        zoom=zoom,
        quick=quick,
        ctx=ctx,
    )


if __name__ == "__main__":
    mcp.run()
