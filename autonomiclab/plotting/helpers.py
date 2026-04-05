"""Shared pyqtgraph drawing primitives used across all protocol plotters."""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pyqtgraph as pg

from autonomiclab.core.models import Marker

_DashLine  = pg.QtCore.Qt.PenStyle.DashLine
_SolidLine = pg.QtCore.Qt.PenStyle.SolidLine


_Y_AXIS_WIDTH = 62  # px — fixed so all plot areas align vertically


def style_plot(plot: pg.PlotItem) -> None:
    """Add grid and draw a full box frame around the plot."""
    plot.showGrid(x=True, y=True, alpha=0.3)
    for axis in ("left", "bottom", "top", "right"):
        plot.getAxis(axis).setPen(pg.mkPen(color="k", width=1))
    # White plot area against the colored widget background
    plot.getViewBox().setBackgroundColor("#ffffff")
    plot.getAxis("left").setWidth(_Y_AXIS_WIDTH)


def shade_region(
    plot: pg.PlotItem,
    ta: Optional[float],
    tb: Optional[float],
    rgba: tuple[int, int, int, int],
) -> None:
    if ta is None or tb is None or tb <= ta:
        return
    r, g, b, a = rgba
    item = pg.LinearRegionItem(
        values=(ta, tb), orientation="vertical",
        brush=pg.mkBrush(r, g, b, a), pen=pg.mkPen(None), movable=False,
    )
    item.setZValue(-10)
    plot.addItem(item)


def add_vline(
    plot: pg.PlotItem,
    t: Optional[float],
    color: str,
    style=_DashLine,
    width: float = 1.5,
) -> None:
    if t is None:
        return
    plot.addItem(pg.InfiniteLine(
        pos=t, angle=90,
        pen=pg.mkPen(color=color, width=width, style=style),
    ))


def add_hline_seg(
    plot: pg.PlotItem,
    t1: Optional[float],
    t2: Optional[float],
    y: Optional[float],
    color: str,
    style=_DashLine,
    width: float = 1.5,
) -> None:
    if t1 is None or t2 is None or y is None:
        return
    plot.addItem(pg.PlotDataItem(
        x=[t1, t2], y=[y, y],
        pen=pg.mkPen(color=color, width=width, style=style),
    ))


def add_vline_seg(
    plot: pg.PlotItem,
    t: Optional[float],
    y1: Optional[float],
    y2: Optional[float],
    color: str,
    style=_SolidLine,
    width: float = 2,
) -> None:
    if t is None or y1 is None or y2 is None:
        return
    plot.addItem(pg.PlotDataItem(
        x=[t, t], y=[y1, y2],
        pen=pg.mkPen(color=color, width=width, style=style),
    ))


def add_dot(
    plot: pg.PlotItem,
    t: Optional[float],
    v: Optional[float],
    color: str,
    size: int = 8,
) -> None:
    if t is None or v is None:
        return
    item = pg.ScatterPlotItem(
        x=[t], y=[v], size=size, symbol="o",
        pen=pg.mkPen(color, width=1.5),
        brush=pg.mkBrush(color),
    )
    plot.addItem(item)
    if plot.legend is not None:
        try:
            plot.legend.removeItem(item)
        except Exception:
            pass


def add_label(
    plot: pg.PlotItem,
    t: Optional[float],
    v: Optional[float],
    txt: str,
    color: str,
    anchor: tuple[float, float] = (0.5, 1.0),
    dy: float = 0,
) -> None:
    if t is None or v is None:
        return
    item = pg.TextItem(txt, color=color, anchor=anchor)
    item.setPos(t, v + dy)
    plot.addItem(item)


def add_draggable_dot(
    plot: pg.PlotItem,
    t_init: float,
    sig_t: np.ndarray,
    sig_v: np.ndarray,
    color: str,
    on_moved: Callable[[float], None],
    size: int = 10,
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    symbol: str = "o",
) -> tuple[pg.ScatterPlotItem, pg.InfiniteLine]:
    """A dot locked to a signal curve that the investigator can drag.

    The drag handle is a movable ``InfiniteLine``; the visible dot follows it,
    snapping to the nearest sample in ``(sig_t, sig_v)``.
    ``on_moved(new_t)`` is called when the drag is released.

    Returns ``(dot, vline)`` so callers can update them later if needed.
    """
    def _snap(t_req: float):
        t_req = float(np.clip(t_req, sig_t[0], sig_t[-1]))
        i = int(np.argmin(np.abs(sig_t - t_req)))
        return float(sig_t[i]), float(sig_v[i])

    t0, v0 = _snap(t_init)

    vline = pg.InfiniteLine(
        pos=t0, angle=90, movable=True,
        pen=pg.mkPen(color=color, width=1, style=_DashLine),
        hoverPen=pg.mkPen(color=color, width=2),
    )
    bounds = [
        t_min if t_min is not None else -1e12,
        t_max if t_max is not None else  1e12,
    ]
    vline.setBounds(bounds)

    dot = pg.ScatterPlotItem(
        x=[t0], y=[v0], size=size, symbol=symbol,
        pen=pg.mkPen(color, width=2), brush=pg.mkBrush(color),
    )

    plot.addItem(vline)
    plot.addItem(dot)

    def _on_dragged() -> None:
        t, v = _snap(vline.value())
        dot.setData(x=[t], y=[v])

    def _on_finished() -> None:
        t, v = _snap(vline.value())
        vline.setValue(t)
        dot.setData(x=[t], y=[v])
        on_moved(t)

    vline.sigDragged.connect(_on_dragged)
    vline.sigPositionChangeFinished.connect(_on_finished)
    return dot, vline


def add_marker_vlines(
    plot: pg.PlotItem,
    markers: list[Marker],
    t_start: Optional[float] = None,
    t_end: Optional[float] = None,
) -> None:
    """Draw a red dashed vertical line for each marker in range."""
    for m in markers:
        if t_start is not None and not (t_start <= m.time <= t_end):
            continue
        plot.addItem(pg.InfiniteLine(
            pos=m.time, angle=90,
            pen=pg.mkPen("r", width=1, style=_DashLine),
        ))


def add_hr_ecg_markers(
    plot_widget: pg.GraphicsLayoutWidget,
    plot: pg.PlotItem,
    dataset,
    t_start: float,
    t_end: float,
) -> None:
    """Overlay HR ECG (RR-int) as small circle markers when available."""
    import numpy as np

    sig = dataset.get_signal("HR ECG (RR-int)")
    if not sig:
        return
    sliced = sig.slice(t_start, t_end)
    if not sliced:
        return
    curve = plot.plot(
        sliced.times, sliced.values,
        pen=None, symbol="o", symbolSize=5,
        symbolPen=pg.mkPen(color="#006400", width=1.5),
        symbolBrush=pg.mkBrush(None),
        name="HR ECG (RR-int)",
    )
    if hasattr(plot_widget, "_plot_curves"):
        plot_widget._plot_curves.setdefault(id(plot), []).append(curve)
