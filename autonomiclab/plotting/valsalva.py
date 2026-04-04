"""Valsalva plot — drawing only. Receives a ValsalvaResult from the analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pyqtgraph as pg

from autonomiclab.analysis.valsalva import ValsalvaResult
from autonomiclab.core.models import Dataset
from autonomiclab.plotting.helpers import (
    add_dot, add_hline_seg, add_label, add_marker_vlines, add_vline,
    add_vline_seg, shade_region, style_plot, add_hr_ecg_markers,
)
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

# Phase fill colours matching Novak 2011 illustration
_FILL = {
    "baseline":     (232, 244, 232, 130),
    "anticipatory": (255, 255, 255,   0),
    "S1":           (255, 243, 224, 120),
    "S2early":      (255, 235, 238, 120),
    "S2late":       (255, 235, 238, 120),
    "S3":           (237, 231, 246, 110),
    "S4":           (224, 247, 250, 110),
}
_BL   = "#2e7d32"
_PI   = "#e65100"
_PII  = "#c62828"
_PIII = "#283593"
_PIV  = "#006064"

_DashLine  = pg.QtCore.Qt.PenStyle.DashLine
_SolidLine = pg.QtCore.Qt.PenStyle.SolidLine

_BP_SIGNALS = {
    "reBAP": ("#808080", 1),
    "reSYS": ("#FF0000", 2),
    "reDIA": ("#00AA00", 2),
    "reMAP": ("#0000FF", 2),
}


class ValsalvaPlotter:
    """Draw the Valsalva three-panel plot and trigger export."""

    def plot(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        dataset: Dataset,
        result: ValsalvaResult,
        t_start: float,
        t_end: float,
        output_dir: Optional[Path] = None,
    ) -> None:
        log.debug("ValsalvaPlotter.plot called")
        plot_widget.clear()
        plot_widget._plot_curves = {}

        hr = dataset.get_signal("HR")
        pa = dataset.get_signal("PAirway")
        if not hr or not pa:
            log.warning("Valsalva plot: missing HR or PAirway signal")
            return

        hr_s = hr.slice(t_start, t_end)
        pa_s = pa.slice(t_start, t_end)

        plot1 = plot_widget.addPlot(row=0, col=0, title="Blood Pressure (Multiple Traces)", rowspan=1)
        plot2 = plot_widget.addPlot(row=1, col=0, title="Heart Rate", rowspan=2)
        plot3 = plot_widget.addPlot(row=3, col=0, title="Airway Pressure", rowspan=1)

        for pid in (id(plot1), id(plot2), id(plot3)):
            plot_widget._plot_curves[pid] = []

        plot2.setXLink(plot1)
        plot3.setXLink(plot1)

        # ── subplot 1: BP ─────────────────────────────────────────────────────
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

        # ── subplot 2: HR ─────────────────────────────────────────────────────
        plot2.addLegend(offset=(10, 10))
        hr_curve = plot2.plot(hr_s.times, hr_s.values,
                              pen=pg.mkPen(color="#8B0000", width=2.5), name="HR (AP)")
        plot_widget._plot_curves[id(plot2)].append(hr_curve)
        plot2.setLabel("left", "HR (bpm)")
        style_plot(plot2)
        add_marker_vlines(plot2, dataset.markers, t_start, t_end)

        # ── subplot 3: PAirway ────────────────────────────────────────────────
        plot3.addLegend(offset=(10, 10))
        pa_curve = plot3.plot(pa_s.times, pa_s.values,
                              pen=pg.mkPen(color="#0078d4", width=2), name="PAirway")
        plot_widget._plot_curves[id(plot3)].append(pa_curve)
        plot3.setLabel("left", "PAirway (mmHg)")
        plot3.setLabel("bottom", "Time (s)")
        style_plot(plot3)
        add_marker_vlines(plot3, dataset.markers, t_start, t_end)

        plot1.setXRange(t_start, t_end)

        # ── draw analysis annotations ─────────────────────────────────────────
        self._draw_annotations(plot1, plot2, plot3, dataset, result)

        # Zoom to analysis window
        if result.t_S1s and result.t_S4e:
            plot1.setXRange(result.t_S1s - 60, result.t_S4e + 15)

        # ── export ────────────────────────────────────────────────────────────
        if output_dir:
            self._export(plot_widget, plot1, plot2, plot3, result, output_dir)

        log.debug("ValsalvaPlotter complete")

    def _draw_annotations(
        self,
        plot_bp: pg.PlotItem,
        plot_hr: pg.PlotItem,
        plot_pa: pg.PlotItem,
        dataset: Dataset,
        r: ValsalvaResult,
    ) -> None:
        # Phase boxes on all three subplots
        for p in (plot_bp, plot_hr, plot_pa):
            shade_region(p, r.t_bl_s,  r.t_bl_e,  _FILL["baseline"])
            shade_region(p, r.t_bl_e,  r.t_S1s,   _FILL["anticipatory"])
            shade_region(p, r.t_S1s,   r.t_S1e,   _FILL["S1"])
            shade_region(p, r.t_S1e,   r.t_S2es,  _FILL["S2early"])
            shade_region(p, r.t_S2es,  r.t_S3s,   _FILL["S2late"])
            shade_region(p, r.t_S3s,   r.t_S3e,   _FILL["S3"])
            shade_region(p, r.t_S3e,   r.t_S4e,   _FILL["S4"])

        # Baseline SBP horizontal
        if r.avg_sbp is not None:
            plot_bp.addItem(pg.InfiniteLine(
                pos=r.avg_sbp, angle=0,
                pen=pg.mkPen(color=_BL, width=1.5, style=_DashLine)))

        # Points #1/#2 baseline boundaries
        add_vline(plot_bp, r.t_bl_s, _BL)
        add_vline(plot_bp, r.t_bl_e, _BL)

        # Point #3 S1 start
        for p in (plot_bp, plot_hr, plot_pa):
            add_vline(p, r.t_S1s, _PI, width=2)

        # Point #4 S1 end dot
        add_dot(plot_bp, r.t_S1e, self._sys_at(dataset, r.t_S1e), _PI)

        # Point #5 IIe nadir + A bracket
        if r.t_S2es and r.v_nadir is not None:
            add_dot(plot_bp, r.t_S2es, r.v_nadir, _PII)
            if r.avg_sbp and r.A is not None:
                add_vline_seg(plot_bp, r.t_S2es, r.v_nadir, r.avg_sbp, _PII, _DashLine)
                add_label(plot_bp, r.t_S2es - 1.5, (r.v_nadir + r.avg_sbp) / 2,
                          f"A={r.A:.0f}", _PII, anchor=(1.0, 0.5))

        # Point #6 S2late max dot
        add_dot(plot_bp, r.t_S2lmax, r.v_S2lmax, _PI)

        # Point #7 S3 start
        for p in (plot_bp, plot_hr, plot_pa):
            add_vline(p, r.t_S3s, _PIII, width=2)

        # Point #8 S3 min + B bracket
        if r.t_S3e and r.v_S3min is not None:
            add_dot(plot_bp, r.t_S3e, r.v_S3min, _PIII)
            if r.t_S2lmax and r.v_S2lmax and r.B is not None:
                t_b = (r.t_S3s - 2.0) if r.t_S3s else (r.t_S2lmax + r.t_S3e) / 2
                add_hline_seg(plot_bp, r.t_S2lmax, t_b, r.v_S2lmax, _PI)
                add_hline_seg(plot_bp, r.t_S2lmax, t_b, r.v_S3min,  _PIII)
                add_vline_seg(plot_bp, t_b, r.v_S3min, r.v_S2lmax, _PIII)
                add_label(plot_bp, t_b - 0.5, (r.v_S2lmax + r.v_S3min) / 2,
                          f"B={r.B:.0f}", _PIII, anchor=(1.0, 0.5))

        # Point #9 PRT
        if r.t_prt_end and r.t_S3e and r.avg_sbp:
            add_dot(plot_bp, r.t_prt_end, r.avg_sbp, _PIII)
            add_hline_seg(plot_bp, r.t_S3e, r.t_prt_end, r.avg_sbp, _PIII, _SolidLine, 2)
            add_label(plot_bp, (r.t_S3e + r.t_prt_end) / 2, r.avg_sbp,
                      f"PRT={r.PRT:.1f}s" if r.PRT else "PRT", _PIII,
                      anchor=(0.5, 1.0), dy=2)

        # Point #10 SBP overshoot
        add_dot(plot_bp, r.t_ov, r.v_ov, _PIV)
        if r.t_ov and r.v_ov:
            add_label(plot_bp, r.t_ov, r.v_ov, "SBP\nOvershoot", _PIV, anchor=(0.5, 1.0), dy=2)

        # Points #11/#12 HR max/min + VR bracket
        add_dot(plot_hr, r.hr_max_t, r.hr_max_v, _PIII)
        if r.hr_max_t and r.hr_max_v:
            add_label(plot_hr, r.hr_max_t, r.hr_max_v,
                      f"HR max\n{r.hr_max_v:.1f}", _PIII, anchor=(0.5, 1.0), dy=1)
        add_dot(plot_hr, r.hr_min_t, r.hr_min_v, _PIV)
        if r.hr_min_t and r.hr_min_v:
            add_label(plot_hr, r.hr_min_t, r.hr_min_v,
                      f"HR min\n{r.hr_min_v:.1f}", _PIV, anchor=(0.5, 0.0), dy=-1)

        if r.hr_max_t and r.hr_min_t and r.t_S4e:
            add_hline_seg(plot_hr, r.hr_max_t, r.t_S4e, r.hr_max_v, _PIII)
            add_hline_seg(plot_hr, r.hr_min_t, r.t_S4e, r.hr_min_v, _PIV)
            add_vline_seg(plot_hr, r.t_S4e, r.hr_min_v, r.hr_max_v, _PIV)
            if r.VR:
                add_label(plot_hr, r.t_S4e + 1, (r.hr_max_v + r.hr_min_v) / 2,
                          f"VR={r.VR:.2f}", _PIV, anchor=(0.0, 0.5))

        # HR subplot y-range
        hr_sig = dataset.get_signal("HR")
        if hr_sig and r.hr_max_v:
            t_zoom_s = (r.t_S1s - 60) if r.t_S1s else hr_sig.t_start
            t_zoom_e = r.t_S4e if r.t_S4e else hr_sig.t_end
            sliced = hr_sig.slice(t_zoom_s, t_zoom_e)
            if sliced:
                y_min = float(np.min(sliced.values)) - 10
                plot_hr.setYRange(y_min, r.hr_max_v + 10)

    @staticmethod
    def _sys_at(dataset: Dataset, t: Optional[float]) -> Optional[float]:
        """Interpolate reSYS value at time t."""
        if t is None:
            return None
        sig = dataset.get_signal("reSYS")
        if not sig:
            return None
        return float(np.interp(t, sig.times, sig.values))

    def _export(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        plot1: pg.PlotItem,
        plot2: pg.PlotItem,
        plot3: pg.PlotItem,
        result: ValsalvaResult,
        output_dir: Path,
    ) -> None:
        from autonomiclab.export.excel import ExcelExporter
        from autonomiclab.export.image import ImageExporter as ImgExp

        img_exp  = ImgExp()
        xls_exp  = ExcelExporter()

        png_full = output_dir / f"{output_dir.name}_valsalva_plot.png"
        img_exp.export_scene(plot_widget, png_full)

        png_zoom = None
        if result.t_S1s and result.t_S4e:
            png_zoom = output_dir / f"{output_dir.name}_valsalva_plot_zoom.png"
            img_exp.export_zoomed_scene(
                plot_widget,
                [plot1, plot2, plot3],
                result.t_S1s - 5,
                result.t_S4e + 5,
                png_zoom,
            )
            # Restore zoom after export
            if result.t_S1s and result.t_S4e:
                plot1.setXRange(result.t_S1s - 60, result.t_S4e + 15)

        xlsx_path = xls_exp.export_valsalva(result, output_dir)
        xls_exp.embed_images_valsalva(xlsx_path, png_full, png_zoom)
