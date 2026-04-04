"""Stand Test plotter — BP (top) + HR (bottom)."""

from __future__ import annotations

import pyqtgraph as pg

from autonomiclab.analysis.stand import StandResult
from autonomiclab.core.models import Dataset
from autonomiclab.plotting.helpers import (
    add_hr_ecg_markers, add_marker_vlines, style_plot,
)
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_BP_SIGNALS = {
    "reBAP": ("#C4C4C4", 1),
    "reSYS": ("#FF0000", 2),
    "reDIA": ("#00AA00", 2),
    "reMAP": ("#0000FF", 2),
}


class StandPlotter:
    """Draw the Stand Test two-panel plot."""

    def plot(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        dataset: Dataset,
        result: StandResult,
        t_start: float,
        t_end: float,
        **_kwargs,
    ) -> None:
        log.debug("StandPlotter.plot called")
        plot_widget.clear()
        plot_widget._plot_curves = {}

        hr = dataset.get_signal("HR")
        if not hr:
            log.warning("Stand plot: HR signal not available")
            return

        hr_s = hr.slice(t_start, t_end)

        plot1 = plot_widget.addPlot(row=0, col=0, title="Blood Pressure (Multiple Traces)", rowspan=1)
        plot2 = plot_widget.addPlot(row=1, col=0, title="Heart Rate", rowspan=2)

        plot_widget._plot_curves[id(plot1)] = []
        plot_widget._plot_curves[id(plot2)] = []

        plot2.setXLink(plot1)

        # BP subplot
        plot1.addLegend(offset=(10, 10))
        for sig_name, (color, width) in _BP_SIGNALS.items():
            sig = dataset.get_signal(sig_name)
            if sig:
                sliced = sig.slice(t_start, t_end)
                if sliced:
                    curve = plot1.plot(sliced.times, sliced.values,
                                       pen=pg.mkPen(color=color, width=width), name=sig_name)
                    plot_widget._plot_curves[id(plot1)].append(curve)
        plot1.setLabel("left", "BP (mmHg)")
        style_plot(plot1)
        add_marker_vlines(plot1, dataset.markers, t_start, t_end)

        # HR subplot
        plot2.addLegend(offset=(10, 10))
        hr_curve = plot2.plot(hr_s.times, hr_s.values,
                              pen=pg.mkPen(color="#8B0000", width=2), name="HR (AP)")
        plot_widget._plot_curves[id(plot2)].append(hr_curve)
        add_hr_ecg_markers(plot_widget, plot2, dataset, t_start, t_end)
        plot2.setLabel("left", "HR (bpm)")
        plot2.setLabel("bottom", "Time (s)")
        style_plot(plot2)
        add_marker_vlines(plot2, dataset.markers, t_start, t_end)

        plot1.setXRange(t_start, t_end)
        log.debug("StandPlotter complete")
