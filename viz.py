from __future__ import annotations

from io import StringIO
from typing import Any

import holoviews as hv
import pandas as pd
import panel as pn
from bokeh.resources import INLINE

from models import validate_plot_request


pn.extension()
hv.extension("bokeh")


def _make_plot(df: pd.DataFrame, plot_type: str, x: str, y: str) -> hv.Element:
    if plot_type == "scatter":
        return hv.Scatter(df, kdims=x, vdims=y).opts(
            size=8,
            tools=["hover"],
            height=400,
            responsive=True,
        )

    if plot_type == "line":
        return hv.Curve(df, kdims=x, vdims=y).opts(
            tools=["hover"],
            line_width=2,
            height=400,
            responsive=True,
        )

    return hv.Bars(df, kdims=x, vdims=y).opts(
        tools=["hover"],
        height=400,
        responsive=True,
    )


def render_plot(
    data: list[dict[str, Any]], plot_type: str, x: str, y: str
) -> str:
    request = validate_plot_request(data=data, plot_type=plot_type, x=x, y=y)
    df = pd.DataFrame(request.data)

    plot = _make_plot(df=df, plot_type=request.plot_type, x=request.x, y=request.y)

    layout = pn.Column(
        f"## Simple {request.plot_type.title()} Plot",
        pn.pane.HoloViews(plot, sizing_mode="stretch_width"),
        sizing_mode="stretch_width",
    )

    html_buffer = StringIO()
    layout.save(html_buffer, resources=INLINE, embed=True, title="MCP HoloViz Plot")
    return html_buffer.getvalue()
