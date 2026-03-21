from __future__ import annotations

import json
from textwrap import dedent

from models import PlotRequest


def _plot_expression(request: PlotRequest) -> str:
    x = json.dumps(request.x)
    y = json.dumps(request.y)

    if request.plot_type == "scatter":
        return dedent(
            f"""
            hv.Scatter(df, kdims={x}, vdims={y}).opts(
                size=8,
                tools=["hover"],
                height=400,
                responsive=True,
            )
            """
        ).strip()

    if request.plot_type == "line":
        return dedent(
            f"""
            hv.Curve(df, kdims={x}, vdims={y}).opts(
                tools=["hover"],
                line_width=2,
                height=400,
                responsive=True,
            )
            """
        ).strip()

    return dedent(
        f"""
        hv.Bars(df, kdims={x}, vdims={y}).opts(
            tools=["hover"],
            height=400,
            responsive=True,
        )
        """
    ).strip()


def build_visualization_code(request: PlotRequest) -> str:
    data_json = json.dumps(request.data, ensure_ascii=True)
    plot_expression = _plot_expression(request)

    return "\n".join(
        [
            "import json",
            "",
            "import holoviews as hv",
            "import pandas as pd",
            "",
            'hv.extension("bokeh")',
            "",
            f"data = json.loads({json.dumps(data_json)})",
            "df = pd.DataFrame(data)",
            "",
            plot_expression,
        ]
    )
