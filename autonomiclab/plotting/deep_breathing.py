"""Deep Breathing plotter — HR with RSA cycle annotations + inline table."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pyqtgraph as pg

from autonomiclab.analysis.deep_breathing import DeepBreathingResult, RSACycle
from autonomiclab.core.models import Dataset
from autonomiclab.plotting.deep_breathing_cycles import CycleInteractor
from autonomiclab.plotting.helpers import add_marker_vlines, style_plot
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_C_INSP = "#B71C1C"   # dark red  — HR max (inspiration)
_C_EXP  = "#1A237E"   # dark blue — HR min (expiration)
_DashLine = pg.QtCore.Qt.PenStyle.DashLine


class DeepBreathingPlotter:
    """Draw the Deep Breathing HR plot with RSA annotations and embedded table."""

    def plot(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        dataset: Dataset,
        result: DeepBreathingResult,
        t_start: float,
        t_end: float,
        on_cycle_override: Optional[Callable] = None,
    ) -> None:
        log.debug("DeepBreathingPlotter.plot called")
        plot_widget.clear()
        plot_widget._plot_curves = {}

        hr = dataset.get_signal("HR")
        if not hr:
            log.warning("Deep breathing plot: HR signal not available")
            return

        hr_s = hr.slice(t_start, t_end)

        plot1 = plot_widget.addPlot(row=0, col=0, title="Heart Rate (RSA)", rowspan=1)
        plot_widget._plot_curves[id(plot1)] = []

        # HR curve
        plot1.addLegend(offset=(10, 10))
        hr_curve = plot1.plot(hr_s.times, hr_s.values,
                              pen=pg.mkPen(color="#8B0000", width=2), name="HR (AP)")
        plot_widget._plot_curves[id(plot1)].append(hr_curve)
        plot1.setLabel("left", "HR (bpm)")
        style_plot(plot1)
        add_marker_vlines(plot1, dataset.markers, t_start, t_end)

        # ── Embedded table (pyqtgraph proxy widget) ───────────────────────────
        table_widget = self._build_table(result)
        from pyqtgraph.Qt.QtWidgets import QGraphicsProxyWidget
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(table_widget)
        plot_widget.ci.addItem(proxy, row=1, col=0)
        plot_widget.ci.layout.setRowStretchFactor(0, 1)
        plot_widget.ci.layout.setRowStretchFactor(1, 1)

        # ── Guided breathing phase box (DBM2–DBM3) ────────────────────────────
        if result.t_dbm2 and result.t_dbm3:
            region = pg.LinearRegionItem(
                values=(result.t_dbm2, result.t_dbm3), orientation="vertical",
                brush=pg.mkBrush(224, 240, 255, 120), pen=pg.mkPen(None), movable=False,
            )
            region.setZValue(-10)
            plot1.addItem(region)
            for t_bnd in (result.t_dbm2, result.t_dbm3):
                plot1.addItem(pg.InfiniteLine(
                    pos=t_bnd, angle=90,
                    pen=pg.mkPen(color="#1565C0", width=2,
                                 style=pg.QtCore.Qt.PenStyle.DashLine)))
            lbl = pg.TextItem("Guided breathing\n5s insp / 5s exp",
                              color="#1565C0", anchor=(0.5, 1.0))
            hr_max_in_window = float(np.max(hr_s.values)) if len(hr_s.values) else 80
            lbl.setPos((result.t_dbm2 + result.t_dbm3) / 2, hr_max_in_window)
            plot1.addItem(lbl)

        # 5-cycle average window
        t_avg_s = next((m.time for m in dataset.markers if "start 5-cycle" in m.label.lower()), None)
        t_avg_e = next((m.time for m in dataset.markers if "end 5-cycle"   in m.label.lower()), None)
        if t_avg_s and t_avg_e:
            reg = pg.LinearRegionItem(
                values=(t_avg_s, t_avg_e), orientation="vertical",
                brush=pg.mkBrush(255, 243, 205, 100), pen=pg.mkPen(None), movable=False,
            )
            reg.setZValue(-9)
            plot1.addItem(reg)

        # ── RSA cycle dots (interactive if callback provided) ─────────────────
        _t_hr = np.asarray(hr_s.times)
        _v_hr = np.asarray(hr_s.values)
        if on_cycle_override:
            self._draw_interactive_cycles(
                plot1, result, _t_hr, _v_hr, on_cycle_override)
        else:
            for cycle in result.cycles:
                plot1.addItem(pg.ScatterPlotItem(
                    x=[cycle.max_t], y=[cycle.max_v], size=10, symbol="t",
                    pen=pg.mkPen(_C_INSP, width=1.5), brush=pg.mkBrush(_C_INSP),
                ))
                plot1.addItem(pg.ScatterPlotItem(
                    x=[cycle.min_t], y=[cycle.min_v], size=10, symbol="t1",
                    pen=pg.mkPen(_C_EXP, width=1.5), brush=pg.mkBrush(_C_EXP),
                ))

        # ── Y/X range ────────────────────────────────────────────────────────
        plot1.disableAutoRange()
        if result.t_dbm2 and result.t_dbm3:
            plot1.setXRange(result.t_dbm2 - 10, result.t_dbm3 + 10, padding=0)
        if len(hr_s.values):
            y_min = float(np.min(hr_s.values))
            y_max = float(np.max(hr_s.values))
            plot1.setYRange(y_min - 5, y_max + 8, padding=0)
        plot1.getViewBox().setAutoPan(x=False, y=False)
        plot1.getViewBox().setAutoVisible(x=False, y=False)

        log.debug("DeepBreathingPlotter complete")

    # ── interactive cycle editing ─────────────────────────────────────────────

    def _draw_interactive_cycles(
        self,
        plot: pg.PlotItem,
        result: DeepBreathingResult,
        t_hr: np.ndarray,
        v_hr: np.ndarray,
        on_cycle_override: Callable,
    ) -> None:
        # Store on self so the instance (and its signal connections) is not
        # garbage-collected before the user interacts with the plot.
        self._cycle_interactor = CycleInteractor(plot, result, t_hr, v_hr, on_cycle_override)

    # ── table builder ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_table(result: DeepBreathingResult):
        from pyqtgraph.Qt import QtWidgets
        table = QtWidgets.QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(
            ["#", "HR max", "t max (s)", "HR min", "t min (s)", "ΔHR", "Top 6"])
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(
            6, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget { font-size: 12px; gridline-color: #cccccc; }
            QHeaderView::section { background-color: #1F4E79; color: white;
                                   font-weight: bold; padding: 4px; }
            QTableWidget::item:alternate { background-color: #f0f4f8; }
        """)

        if not result.cycles:
            return table

        def _cell(txt, color=None, bold=False, bg=None):
            item = QtWidgets.QTableWidgetItem(str(txt))
            item.setTextAlignment(pg.QtCore.Qt.AlignmentFlag.AlignCenter)
            if color:
                item.setForeground(pg.mkColor(color))
            if bold:
                f = item.font(); f.setBold(True); item.setFont(f)
            if bg:
                item.setBackground(pg.mkColor(bg))
            return item

        table.setRowCount(len(result.cycles) + 2)
        for ri, c in enumerate(result.cycles):
            selected = c.cycle in result.top6
            bg = "#F1F8E9" if selected else None
            table.setItem(ri, 0, _cell(c.cycle,               bg=bg))
            table.setItem(ri, 1, _cell(f"{c.max_v:.1f}", "#8B0000", bg=bg))
            table.setItem(ri, 2, _cell(f"{c.max_t:.1f}",              bg=bg))
            table.setItem(ri, 3, _cell(f"{c.min_v:.1f}", "#1A237E", bg=bg))
            table.setItem(ri, 4, _cell(f"{c.min_t:.1f}",              bg=bg))
            table.setItem(ri, 5, _cell(f"{c.rsa:.1f}",                bg=bg))
            table.setItem(ri, 6, _cell("✓" if selected else "",
                                       "#2E7D32" if selected else None,
                                       bold=selected, bg=bg))

        mr_all = len(result.cycles)
        BG_ALL = "#F5F5F5"
        table.setItem(mr_all, 0, _cell(f"Mean (n={len(result.valid_cycles)})", bold=True, bg=BG_ALL))
        table.setItem(mr_all, 1, _cell(f"{result.mean_max_all:.1f}", "#8B0000", bold=True, bg=BG_ALL))
        table.setItem(mr_all, 2, _cell("", bg=BG_ALL))
        table.setItem(mr_all, 3, _cell(f"{result.mean_min_all:.1f}", "#1A237E", bold=True, bg=BG_ALL))
        table.setItem(mr_all, 4, _cell("", bg=BG_ALL))
        table.setItem(mr_all, 5, _cell(f"{result.avg_rsa_all:.1f}", "#555555", bold=True, bg=BG_ALL))
        table.setItem(mr_all, 6, _cell("", bg=BG_ALL))

        mr_top = len(result.cycles) + 1
        BG_TOP = "#E8F5E9"
        table.setItem(mr_top, 0, _cell(f"Mean (top {result.n_sel})", bold=True, bg=BG_TOP))
        table.setItem(mr_top, 1, _cell(f"{result.mean_max_top:.1f}", "#8B0000", bold=True, bg=BG_TOP))
        table.setItem(mr_top, 2, _cell("", bg=BG_TOP))
        table.setItem(mr_top, 3, _cell(f"{result.mean_min_top:.1f}", "#1A237E", bold=True, bg=BG_TOP))
        table.setItem(mr_top, 4, _cell("", bg=BG_TOP))
        table.setItem(mr_top, 5, _cell(f"{result.avg_rsa_top6:.1f}", "#1B5E20", bold=True, bg=BG_TOP))
        table.setItem(mr_top, 6, _cell("✓", "#2E7D32", bold=True, bg=BG_TOP))

        return table

    def export(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        result: DeepBreathingResult,
        output_dir: Path,
        mode: str = "auto",
    ) -> None:
        from autonomiclab.export.excel import ExcelExporter
        from autonomiclab.export.image import ImageExporter as ImgExp

        png_path = output_dir / f"{output_dir.parent.name}_deep_breathing_results.png"
        ImgExp().export_scene(plot_widget, png_path)

        xlsx_path = ExcelExporter().export_deep_breathing(result, output_dir, mode)
        if png_path.exists():
            ExcelExporter().embed_image_deep_breathing(xlsx_path, png_path)
