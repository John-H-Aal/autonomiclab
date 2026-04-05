"""Deep Breathing plotter — HR with RSA cycle annotations + inline table."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

from autonomiclab.analysis.deep_breathing import DeepBreathingResult, RSACycle
from autonomiclab.core.models import Dataset
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
        """Draw draggable cycle dots with right-click delete and double-click insert."""

        def _snap(t_req: float):
            i = int(np.argmin(np.abs(t_hr - t_req)))
            return float(t_hr[i]), float(v_hr[i])

        def _cycles_as_dicts() -> list[dict]:
            return [{"max_t": c.max_t, "min_t": c.min_t} for c in result.cycles]

        def _rebuild_and_notify() -> None:
            on_cycle_override(_cycles_as_dicts())

        def _add_dot_pair(cycle: RSACycle) -> None:
            """Add one draggable max+min pair for a cycle."""

            # ── max dot (inverted triangle ▲) ─────────────────────────────────
            max_dot = pg.ScatterPlotItem(
                x=[cycle.max_t], y=[cycle.max_v], size=11, symbol="t",
                pen=pg.mkPen(_C_INSP, width=2), brush=pg.mkBrush(_C_INSP),
            )
            max_line = pg.InfiniteLine(
                pos=cycle.max_t, angle=90, movable=True,
                pen=pg.mkPen(_C_INSP, width=1, style=_DashLine),
                hoverPen=pg.mkPen(_C_INSP, width=2),
            )

            # ── min dot (inverted triangle ▼) ─────────────────────────────────
            min_dot = pg.ScatterPlotItem(
                x=[cycle.min_t], y=[cycle.min_v], size=11, symbol="t1",
                pen=pg.mkPen(_C_EXP, width=2), brush=pg.mkBrush(_C_EXP),
            )
            min_line = pg.InfiniteLine(
                pos=cycle.min_t, angle=90, movable=True,
                pen=pg.mkPen(_C_EXP, width=1, style=_DashLine),
                hoverPen=pg.mkPen(_C_EXP, width=2),
            )

            for item in (max_dot, max_line, min_dot, min_line):
                plot.addItem(item)

            # ── drag handlers ──────────────────────────────────────────────────
            def _on_max_drag():
                t, v = _snap(max_line.value())
                max_dot.setData(x=[t], y=[v])

            def _on_max_released():
                t, v = _snap(max_line.value())
                max_line.setValue(t)
                max_dot.setData(x=[t], y=[v])
                cycle.max_t, cycle.max_v = t, v
                cycle.rsa = cycle.max_v - cycle.min_v
                _rebuild_and_notify()

            def _on_min_drag():
                t, v = _snap(min_line.value())
                min_dot.setData(x=[t], y=[v])

            def _on_min_released():
                t, v = _snap(min_line.value())
                min_line.setValue(t)
                min_dot.setData(x=[t], y=[v])
                cycle.min_t, cycle.min_v = t, v
                cycle.rsa = cycle.max_v - cycle.min_v
                _rebuild_and_notify()

            max_line.sigDragged.connect(_on_max_drag)
            max_line.sigPositionChangeFinished.connect(_on_max_released)
            min_line.sigDragged.connect(_on_min_drag)
            min_line.sigPositionChangeFinished.connect(_on_min_released)

        for cycle in result.cycles:
            _add_dot_pair(cycle)

        # Disable pyqtgraph's built-in right-click context menu on the ViewBox
        # so we can fully control right-click behaviour ourselves.
        plot.vb.setMenuEnabled(False)

        # ── scene click: right-click delete + double-click insert ─────────────
        # Disconnect any handler registered by a previous plot() call so we
        # never accumulate multiple handlers on the same scene.
        scene = plot.scene()
        old_handler = getattr(scene, "_db_click_handler", None)
        if old_handler is not None:
            try:
                scene.sigMouseClicked.disconnect(old_handler)
            except Exception:
                pass

        _DELETE_RADIUS_S = 2.0   # seconds — how close the click must be to a dot

        def _on_scene_clicked(ev):
            pos = plot.vb.mapSceneToView(ev.scenePos())
            t_click = float(pos.x())

            # ── right-click: find nearest cycle dot and offer delete ───────────
            if ev.button() == QtCore.Qt.MouseButton.RightButton and not ev.double():
                best_cycle = None
                best_dist  = _DELETE_RADIUS_S
                for c in result.cycles:
                    for t_pt in (c.max_t, c.min_t):
                        dist = abs(t_pt - t_click)
                        if dist < best_dist:
                            best_dist  = dist
                            best_cycle = c
                if best_cycle is None:
                    return
                ev.accept()
                menu = QtWidgets.QMenu()
                act = menu.addAction(f"Delete cycle {best_cycle.cycle}")
                def _delete(checked=False, cyc=best_cycle):
                    result.cycles = [x for x in result.cycles if x.cycle != cyc.cycle]
                    for n, x in enumerate(result.cycles, start=1):
                        x.cycle = n
                    QtCore.QTimer.singleShot(0, _rebuild_and_notify)
                act.triggered.connect(_delete)
                # Store menu on scene to prevent garbage collection, then
                # defer exec until after mouse-release is fully processed.
                scene._db_menu = menu
                QtCore.QTimer.singleShot(0, lambda m=menu: m.exec(QtGui.QCursor.pos()))
                return

            # ── double left-click: insert new cycle ───────────────────────────
            if not ev.double():
                return
            if ev.button() != QtCore.Qt.MouseButton.LeftButton:
                return
            pos = plot.vb.mapSceneToView(ev.scenePos())
            t_click = float(pos.x())

            # Find the nearest HR sample to click, then search ±3 s for a local max
            SEARCH = 3.0
            mask = (t_hr >= t_click - SEARCH) & (t_hr <= t_click + SEARCH)
            if not np.any(mask):
                return
            t_w, v_w = t_hr[mask], v_hr[mask]
            i_max = int(np.argmax(v_w))
            new_max_t, new_max_v = float(t_w[i_max]), float(v_w[i_max])

            # Auto-find following min within 6 s
            mask2 = (t_hr > new_max_t) & (t_hr <= new_max_t + 6.0)
            if np.any(mask2):
                t_w2, v_w2 = t_hr[mask2], v_hr[mask2]
                i_min = int(np.argmin(v_w2))
                new_min_t, new_min_v = float(t_w2[i_min]), float(v_w2[i_min])
            else:
                return   # no trough found — ignore insert

            # Avoid duplicates (within 1 s of an existing max)
            for c in result.cycles:
                if abs(c.max_t - new_max_t) < 1.0:
                    return

            new_cycle = RSACycle(
                cycle=len(result.cycles) + 1,
                max_t=new_max_t, max_v=new_max_v,
                min_t=new_min_t, min_v=new_min_v,
                rsa=new_max_v - new_min_v,
            )
            # Insert in time order
            result.cycles.append(new_cycle)
            result.cycles.sort(key=lambda c: c.max_t)
            for n, c in enumerate(result.cycles, start=1):
                c.cycle = n
            _rebuild_and_notify()

        scene.sigMouseClicked.connect(_on_scene_clicked)
        scene._db_click_handler = _on_scene_clicked

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
