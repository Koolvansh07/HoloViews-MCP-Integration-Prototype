from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from models import SUPPORTED_PLOT_TYPES
from viz import render_plot


mcp = FastMCP("mcp-holoviz-prototype")


@mcp.tool(description="Create a simple interactive plot and return it as HTML.")
def create_plot(
    data: list[dict[str, Any]], plot_type: str, x: str, y: str
) -> str:
    return render_plot(data=data, plot_type=plot_type, x=x, y=y)


@mcp.tool(description="List the plot types supported by this prototype.")
def list_plot_types() -> list[str]:
    return SUPPORTED_PLOT_TYPES


if __name__ == "__main__":
    mcp.run()
