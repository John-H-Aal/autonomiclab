"""Shared pyqtgraph drawing primitives used across all protocol plotters."""

from __future__ import annotations

from typing import Optional

import pyqtgraph as pg

from autonomiclab.core.models import Marker

_DashLine  = pg.QtCore.Qt.PenStyle.DashLine
_SolidLine = pg.QtCore.Qt.PenStyle.SolidLine


def style_plot(plot: pg.PlotItem) -> None:
    """Add grid and draw a full box frame around the plot."""
    plot.showGrid(x=True, y=True, alpha=0.3)
    for axis in ("left", "bottom", "top", "right"):
        plot.getAxis(axis).setPen(pg.mkPen(color="k", width=1))


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
