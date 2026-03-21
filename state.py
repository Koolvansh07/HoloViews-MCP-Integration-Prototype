from __future__ import annotations

from dataclasses import dataclass
import threading
import uuid
from typing import Any

from models import PlotRequest, validate_plot_request


class PlotNotFoundError(KeyError):
    """Raised when a plot ID does not exist in the in-memory registry."""


@dataclass(frozen=True)
class PlotRecord:
    plot_id: str
    request: PlotRequest
    version: int


_store: dict[str, PlotRecord] = {}
_lock = threading.Lock()


def create_plot_record(
    *,
    data: list[dict[str, Any]],
    plot_type: str,
    x: str,
    y: str,
) -> PlotRecord:
    request = validate_plot_request(data=data, plot_type=plot_type, x=x, y=y)

    with _lock:
        plot_id = uuid.uuid4().hex[:8]
        record = PlotRecord(plot_id=plot_id, request=request, version=1)
        _store[plot_id] = record
        return record


def get_plot_record(plot_id: str) -> PlotRecord:
    with _lock:
        try:
            return _store[plot_id]
        except KeyError as exc:
            raise PlotNotFoundError(f"No plot found for id: {plot_id}") from exc


def update_plot_record(
    plot_id: str,
    *,
    data: list[dict[str, Any]] | None = None,
    plot_type: str | None = None,
    x: str | None = None,
    y: str | None = None,
) -> PlotRecord:
    with _lock:
        try:
            existing = _store[plot_id]
        except KeyError as exc:
            raise PlotNotFoundError(f"No plot found for id: {plot_id}") from exc

        request = validate_plot_request(
            data=existing.request.data if data is None else data,
            plot_type=existing.request.plot_type if plot_type is None else plot_type,
            x=existing.request.x if x is None else x,
            y=existing.request.y if y is None else y,
        )
        updated = PlotRecord(
            plot_id=plot_id,
            request=request,
            version=existing.version + 1,
        )
        _store[plot_id] = updated
        return updated
