"""Overview plotter — full recording: BP / HR / PAirway."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from autonomiclab.core.models import Dataset
from autonomiclab.plotting.helpers import (
    add_hr_ecg_markers,
    add_marker_vlines,
    style_plot,
)
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_BP_SIGNALS = {
    "reBAP": ("#C0C0C0", 1),
    "reSYS": ("#FF0000", 2),
    "reDIA": ("#00AA00", 2),
    "reMAP": ("#0000FF", 2),
}


class OverviewPlotter:
    """Plot the full recording as three linked subplots."""

    def plot(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        dataset: Dataset,
    ) -> None:
        log.debug("OverviewPlotter.plot called")
        plot_widget.clear()
        plot_widget._plot_curves = {}

        hr = dataset.get_signal("HR")
        if not hr:
            log.warning("Overview plot: HR signal not available")
            return

        t_start, t_end = hr.t_start, hr.t_end

        plot1 = plot_widget.addPlot(row=0, col=0, title="Blood Pressure")
        plot2 = plot_widget.addPlot(row=1, col=0, title="Heart Rate")
        plot3 = plot_widget.addPlot(row=2, col=0, title="Airway")

        plot_widget._plot_curves[id(plot1)] = []
        plot_widget._plot_curves[id(plot2)] = []
        plot_widget._plot_curves[id(plot3)] = []

        plot2.setXLink(plot1)
        plot3.setXLink(plot1)

        # ── BP subplot ────────────────────────────────────────────────────────
        plot1.addLegend(offset=(10, 10))
        for sig_name, (color, width) in _BP_SIGNALS.items():
            sig = dataset.get_signal(sig_name)
            if sig:
                curve = plot1.plot(sig.times, sig.values,
                                   pen=pg.mkPen(color=color, width=width), name=sig_name)
                plot_widget._plot_curves[id(plot1)].append(curve)
        plot1.setLabel("left", "BP (mmHg)")
        style_plot(plot1)
        add_marker_vlines(plot1, dataset.markers)

        # ── HR subplot ────────────────────────────────────────────────────────
        plot2.addLegend(offset=(10, 10))
        curve = plot2.plot(hr.times, hr.values,
                           pen=pg.mkPen(color="#8B0000", width=2), name="HR (AP)")
        plot_widget._plot_curves[id(plot2)].append(curve)
        add_hr_ecg_markers(plot_widget, plot2, dataset, t_start, t_end)
        plot2.setLabel("left", "HR (bpm)")
        style_plot(plot2)
        add_marker_vlines(plot2, dataset.markers)

        # ── PAirway subplot ───────────────────────────────────────────────────
        plot3.addLegend(offset=(10, 10))
        pa = dataset.get_signal("PAirway")
        if pa:
            curve = plot3.plot(pa.times, pa.values,
                               pen=pg.mkPen(color="#0078d4", width=1.5), name="PAirway")
            plot_widget._plot_curves[id(plot3)].append(curve)
        plot3.setLabel("left", "PAirway (mmHg)")
        plot3.setLabel("bottom", "Time (s)")
        style_plot(plot3)
        add_marker_vlines(plot3, dataset.markers)

        plot1.setXRange(t_start, t_end)
        log.debug("OverviewPlotter complete")
