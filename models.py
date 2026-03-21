from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_PLOT_TYPES = ["scatter", "line", "bar"]


@dataclass(frozen=True)
class PlotRequest:
    data: list[dict[str, Any]]
    plot_type: str
    x: str
    y: str

    def validate(self) -> None:
        if not self.data:
            raise ValueError("data must not be empty")

        if self.plot_type not in SUPPORTED_PLOT_TYPES:
            raise ValueError(
                f"plot_type must be one of: {', '.join(SUPPORTED_PLOT_TYPES)}"
            )

        available_columns: set[str] = set()

        for row in self.data:
            if not isinstance(row, dict):
                raise ValueError("each item in data must be a dictionary")
            available_columns.update(row.keys())

        if self.x not in available_columns:
            raise ValueError(f"x column '{self.x}' was not found in the data")

        if self.y not in available_columns:
            raise ValueError(f"y column '{self.y}' was not found in the data")


def validate_plot_request(
    data: list[dict[str, Any]],
    plot_type: str,
    x: str,
    y: str,
) -> PlotRequest:
    request = PlotRequest(data=data, plot_type=plot_type, x=x, y=y)
    request.validate()
    return request
