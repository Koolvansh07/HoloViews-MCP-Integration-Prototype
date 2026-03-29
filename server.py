from __future__ import annotations

import atexit
import json
from pathlib import Path
import subprocess
import sys
import threading
from textwrap import dedent
from typing import Any
from typing import Literal

from fastmcp import Context
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.apps import AppConfig
from fastmcp.server.apps import ResourceCSP

from panel_live_server.client import DisplayClient
from panel_live_server.config import get_config
import panel_live_server.manager as panel_manager_module
from panel_live_server.manager import PanelServerManager
import panel_live_server.server as panel_server

from models import SUPPORTED_PLOT_TYPES
from state import create_plot_record, update_plot_record
from viz import build_visualization_code


mcp = FastMCP(
    "HoloViz Panel MCP",
    instructions=(
        "Use the structured plotting tools first when the user wants a simple "
        "scatter, line, or bar chart from tabular JSON data. These tools return "
        "an MCP App payload for inline rendering when the client supports it. "
        "Use show or interactive_sine_wave when the user wants a richer "
        "interactive Panel app with sliders or widget controls rendered inline "
        "in chat."
    ),
)

_RENDERER_LOCK = threading.Lock()


_PANEL_STARTUP_TIMEOUT_SECONDS = 90


def _tool_name(plot_type: str, plot_id: str, version: int) -> str:
    return f"{plot_type.title()} Plot {plot_id} v{version}"


def _tool_description(x: str, y: str) -> str:
    return f"Interactive visualization of `{y}` against `{x}`."


def _ensure_renderer_ready() -> None:
    with _RENDERER_LOCK:
        if panel_server._client and panel_server._client.is_healthy():
            return

        manager, client = _start_panel_server()
        if not manager or not client:
            raise RuntimeError("Failed to start panel-live-server renderer.")

        panel_server._manager = manager
        panel_server._client = client


def _patch_panel_startup_timeout() -> None:
    original_wait_for_health = PanelServerManager._wait_for_health

    def _wait_for_health_with_longer_timeout(
        self: PanelServerManager,
        timeout: int = _PANEL_STARTUP_TIMEOUT_SECONDS,
        interval: float = 1.0,
    ) -> bool:
        return original_wait_for_health(self, timeout=timeout, interval=interval)

    PanelServerManager._wait_for_health = _wait_for_health_with_longer_timeout


class _StdIOSafePanelServerManager(PanelServerManager):
    """Detach renderer stdin so the child does not inherit the MCP stdio pipe."""

    def start(self) -> bool:
        if self.process and self.process.poll() is None:
            panel_manager_module.logger.info("Panel server is already running")
            return True

        if self._is_port_in_use():
            if self._try_recover_stale_server():
                return True
            if self._is_port_in_use():
                panel_manager_module.logger.error(
                    f"Port {self.port} is still in use, cannot start Panel server"
                )
                return False

        try:
            app_path = Path(panel_manager_module.__file__).parent / "app.py"
            env = self._build_subprocess_env()

            panel_manager_module.logger.info(
                f"Using database at: {env['PANEL_LIVE_SERVER_DB_PATH']}"
            )
            panel_manager_module.logger.info(
                f"Starting Panel server on {self.host}:{self.port}"
            )

            self.process = subprocess.Popen(
                [sys.executable, str(app_path)],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )

            if self._wait_for_health():
                panel_manager_module.logger.info("Panel server started successfully")
                self.restart_count = 0
                return True

            panel_manager_module.logger.error(
                "Panel server failed to start (health check timed out)"
            )
            self.stop()
            return False
        except Exception as e:
            panel_manager_module.logger.exception(f"Error starting Panel server: {e}")
            return False


def _start_panel_server() -> tuple[PanelServerManager | None, DisplayClient | None]:
    config = get_config()
    manager = _StdIOSafePanelServerManager(
        db_path=config.db_path,
        port=config.port,
        host=config.host,
        max_restarts=config.max_restarts,
    )

    if not manager.start():
        panel_manager_module.logger.error("Failed to start Panel server")
        return None, None

    client = DisplayClient(base_url=manager.get_base_url())
    return manager, client


def _render_snippet_payload(
    *,
    code: str,
    name: str,
    description: str,
    method: Literal["jupyter", "panel"],
    zoom: int,
) -> str:
    if not panel_server._client:
        raise ToolError("Panel Live Server client is not available.")

    response = panel_server._client.create_snippet(
        code=code,
        name=name,
        description=description,
        method=method,
    )
    url = panel_server._externalize_url(response.get("url", ""))

    payload: dict[str, str | int] = {
        "tool": "show",
        "name": name,
        "description": description,
        "method": method,
        "zoom": zoom,
        "url": url,
        "code": code,
    }

    if error_message := response.get("error_message"):
        raise ToolError(
            "Visualization created but failed at runtime:\n"
            f"{error_message}\n"
            "Fix the code and try again."
        )

    payload["status"] = "success"
    payload["message"] = "Visualization created successfully."
    return json.dumps(payload)


atexit.register(panel_server._cleanup)
_patch_panel_startup_timeout()


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


@mcp.tool(
    name="list_packages",
    description="List packages available inside the panel-live-server runtime.",
)
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


@mcp.tool(
    name="validate",
    description="Validate Panel or HoloViews code before rendering it inline.",
)
async def validate(
    code: str,
    method: Literal["jupyter", "panel"] = "jupyter",
    ctx: Context | None = None,
) -> dict:
    return await panel_server.validate(code=code, method=method, ctx=ctx)


@mcp.tool(
    name="interactive_sine_wave",
    description="Render an inline interactive HoloViews sine-wave app with sliders for amplitude, frequency, and phase.",
    app=AppConfig(resource_uri=panel_server.SHOW_RESOURCE_URI),
)
async def interactive_sine_wave(
    amplitude: float = 1.0,
    frequency: float = 1.0,
    phase: float = 0.0,
    points: int = 400,
) -> str:
    code = dedent(
        f"""
        import numpy as np
        import holoviews as hv
        import panel as pn

        hv.extension("bokeh")
        pn.extension()

        x = np.linspace(0, 4 * np.pi, {points})


        def make_curve(amplitude, frequency, phase):
            y = amplitude * np.sin(frequency * x + phase)
            return hv.Curve((x, y), "x", "y").opts(
                height=420,
                responsive=True,
                line_width=3,
                tools=["hover"],
                title="Interactive Sine Wave",
            )


        amplitude_slider = pn.widgets.FloatSlider(
            name="Amplitude", start=0.1, end=5.0, step=0.1, value={amplitude}
        )
        frequency_slider = pn.widgets.FloatSlider(
            name="Frequency", start=0.1, end=5.0, step=0.1, value={frequency}
        )
        phase_slider = pn.widgets.FloatSlider(
            name="Phase", start=0.0, end=6.28, step=0.1, value={phase}
        )

        curve = pn.bind(
            make_curve,
            amplitude=amplitude_slider,
            frequency=frequency_slider,
            phase=phase_slider,
        )

        pn.Column(
            "## Interactive Sine Wave",
            "Adjust the sliders to update the HoloViews curve inline.",
            amplitude_slider,
            frequency_slider,
            phase_slider,
            curve,
        )
        """
    ).strip()
    return await show(
        code=code,
        name="Interactive Sine Wave",
        description="HoloViews curve rendered inline with Panel sliders.",
        method="jupyter",
        zoom=100,
        quick=True,
        ctx=None,
    )


@mcp.tool(
    name="show",
    description="Render arbitrary Panel or HoloViews code inline through panel-live-server.",
    app=AppConfig(resource_uri=panel_server.SHOW_RESOURCE_URI),
)
async def show(
    code: str,
    name: str = "",
    description: str = "",
    method: Literal["jupyter", "panel"] = "jupyter",
    zoom: int = 100,
    quick: bool = True,
    ctx: Context | None = None,
) -> str:
    _ensure_renderer_ready()
    valid_zooms = [25, 50, 75, 100]
    zoom = min(valid_zooms, key=lambda candidate: abs(candidate - zoom))

    if quick:
        validation = panel_server._run_validation(code, method)
        if not validation.get("valid", False):
            panel_server._raise_validation_error(validation)
        return _render_snippet_payload(
            code=code,
            name=name,
            description=description,
            method=method,
            zoom=zoom,
        )

    validation = await panel_server.validate(code=code, method=method, ctx=ctx)
    if not validation.get("valid", False):
        layer = validation.get("layer", "validation")
        message = validation.get("message", "Visualization validation failed.")
        raise ToolError(f"[{layer}] {message}")
    return await panel_server.show(
        code=code,
        name=name,
        description=description,
        method=method,
        zoom=zoom,
        quick=False,
        ctx=ctx,
    )


if __name__ == "__main__":
    mcp.run()
