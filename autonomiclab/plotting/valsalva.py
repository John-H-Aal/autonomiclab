"""Valsalva plot — drawing only. Receives a ValsalvaResult from the analyzer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pyqtgraph as pg

from autonomiclab.analysis.valsalva import ValsalvaResult
from autonomiclab.core.models import Dataset
from autonomiclab.plotting.helpers import (
    add_dot, add_draggable_dot, add_hline_seg, add_label, add_marker_vlines,
    add_vline, add_vline_seg, shade_region, style_plot, add_hr_ecg_markers,
)
from autonomiclab.plotting.valsalva_baseline import BaselineRegionInteractor
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

# Phase fill colours matching Novak 2011 illustration
_FILL = {
    "baseline":     (232, 244, 232, 130),
    "anticipatory": (255, 255, 255,   0),
    "S1":           (255, 243, 224, 120),
    "S2early":      (255, 205, 215, 140),
    "S2late":       (255, 160, 180, 150),
    "S3":           (195, 170, 235, 150),
    "S4":           (155, 220, 240, 150),
}
_BL   = "#2e7d32"
_PI   = "#e65100"
_PII  = "#c62828"
_PIII = "#6a1b9a"
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
        on_manual_override: Optional[object] = None,
        on_point_override: Optional[object] = None,
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

        # ── draw analysis annotations ─────────────────────────────────────────
        self._draw_annotations(plot1, plot2, plot3, dataset, result,
                               on_manual_override, on_point_override,
                               t_start=t_start, t_end=t_end)

        # Zoom to analysis window — use the best available right-hand anchor
        # (t_S4e may be None when Phase IV is suppressed due to calibration)
        _zoom_end = (
            result.t_S4e                          # normal case
            or (result.t_S3s + 45 if result.t_S3s else None)  # PIV suppressed
            or (result.t_S3e + 45 if result.t_S3e else None)  # fallback
        )
        if result.t_S1s and _zoom_end:
            plot1.setXRange(result.t_S1s - 60, _zoom_end + 15)

        log.debug("ValsalvaPlotter complete")

    def _add_baseline_region(
        self,
        plot_bp: pg.PlotItem,
        plot_hr: pg.PlotItem,
        plot_pa: pg.PlotItem,
        dataset: Dataset,
        r: ValsalvaResult,
        on_manual_override: Optional[object] = None,
    ) -> None:
        # Store on self so the instance (and its signal connections) is not
        # garbage-collected before the user interacts with the plot.
        self._baseline_interactor = BaselineRegionInteractor(
            plot_bp, plot_hr, plot_pa, dataset, r,
            on_changed=on_manual_override,
        )

    # ── calibration warning overlay ───────────────────────────────────────────

    @staticmethod
    def _draw_cal_warnings(
        plot_bp: pg.PlotItem,
        dataset: Dataset,
        r: ValsalvaResult,
        t_start: float = None,
        t_end: float = None,
    ) -> None:
        """Shade calibration-active periods and show a warning banner on BP plot."""
        cal_sig = dataset.get_signal("PhysioCalActive")
        _CAL_BRUSH  = pg.mkBrush(255, 200, 0, 80)   # amber, semi-transparent
        _CAL_PEN    = pg.mkPen(color="#b8860b", width=1, style=pg.QtCore.Qt.PenStyle.DashLine)
        _WARN_COLOR = "#b8400b"

        # Shade calibration bursts — restricted to the analysis window so bursts
        # from the rest of the recording do not clutter the zoomed view.
        if cal_sig is not None:
            t_c, v_c = cal_sig.times, cal_sig.values
            # Restrict to analysis window if provided
            if t_start is not None and t_end is not None:
                mask = (t_c >= t_start) & (t_c <= t_end)
                t_c, v_c = t_c[mask], v_c[mask]

            in_burst = False
            t_burst_start = None
            for t, v in zip(t_c, v_c):
                if v > 0.5 and not in_burst:
                    in_burst = True
                    t_burst_start = t
                elif v <= 0.5 and in_burst:
                    in_burst = False
                    region = pg.LinearRegionItem(
                        values=(t_burst_start, t),
                        orientation="vertical",
                        brush=_CAL_BRUSH,
                        pen=_CAL_PEN,
                        movable=False,
                    )
                    region.setZValue(5)
                    plot_bp.addItem(region)
            # Close any open burst at end of window
            if in_burst and t_burst_start is not None:
                region = pg.LinearRegionItem(
                    values=(t_burst_start, float(t_c[-1])),
                    orientation="vertical",
                    brush=_CAL_BRUSH,
                    pen=_CAL_PEN,
                    movable=False,
                )
                region.setZValue(5)
                plot_bp.addItem(region)

        # Warning banner top-left of BP plot listing affected regions
        regions_str = " · ".join(r.cal_warnings)
        banner = pg.TextItem(
            f"⚠ Finapres calibration: {regions_str}",
            color=_WARN_COLOR,
            anchor=(0.0, 0.0),
        )
        banner.setZValue(20)
        yr = plot_bp.viewRange()[1]
        xr = plot_bp.viewRange()[0]
        banner.setPos(xr[0], yr[1])
        plot_bp.addItem(banner, ignoreBounds=True)

    def _draw_annotations(
        self,
        plot_bp: pg.PlotItem,
        plot_hr: pg.PlotItem,
        plot_pa: pg.PlotItem,
        dataset: Dataset,
        r: ValsalvaResult,
        on_manual_override: Optional[object] = None,
        on_point_override: Optional[object] = None,
        t_start: float = None,
        t_end: float = None,
    ) -> None:
        # ── Finapres calibration warnings ─────────────────────────────────────
        if r.cal_warnings:
            self._draw_cal_warnings(plot_bp, dataset, r, t_start=t_start, t_end=t_end)

        # Baseline: interactive region handles shade, vlines, avg_sbp line, A bracket
        self._add_baseline_region(plot_bp, plot_hr, plot_pa, dataset, r, on_manual_override)

        # Remaining static phase shades
        for p in (plot_bp, plot_hr, plot_pa):
            shade_region(p, r.t_bl_e,  r.t_S1s,   _FILL["anticipatory"])
            shade_region(p, r.t_S1s,   r.t_S1e,   _FILL["S1"])
            shade_region(p, r.t_S1e,   r.t_S2es,  _FILL["S2early"])
            shade_region(p, r.t_S2es,  r.t_S3s,   _FILL["S2late"])
            shade_region(p, r.t_S3s,   r.t_S3e,   _FILL["S3"])
            shade_region(p, r.t_S3e,   r.t_S4e,   _FILL["S4"])

        # ── helper: build on_moved callback for a named field ─────────────────
        def _cb(field: str):
            if on_point_override is None:
                return lambda t: None
            return lambda t, f=field: on_point_override(f, t)

        # Fetch signal arrays once for draggable dots
        _sys = dataset.get_signal("reSYS")
        _hr  = dataset.get_signal("HR")
        _t_sys = np.asarray(_sys.times)  if _sys else np.array([])
        _v_sys = np.asarray(_sys.values) if _sys else np.array([])
        _t_hr  = np.asarray(_hr.times)   if _hr  else np.array([])
        _v_hr  = np.asarray(_hr.values)  if _hr  else np.array([])

        # Point #3 S1 start (static vline — PAirway-derived, less useful to move)
        for p in (plot_bp, plot_hr, plot_pa):
            add_vline(p, r.t_S1s, _PI, width=2)

        # Point #4 S1 end — draggable on BP (Phase I / IIe boundary)
        if r.t_S1e is not None and len(_t_sys):
            add_draggable_dot(
                plot_bp, r.t_S1e, _t_sys, _v_sys, _PI, _cb("t_S1e"),
                t_min=r.t_S1s, t_max=r.t_S3s,
            )
        else:
            add_dot(plot_bp, r.t_S1e, self._sys_at(dataset, r.t_S1e), _PI)

        # Point #5 IIe nadir — draggable on BP (A bracket drawn in _add_baseline_region)
        if r.t_S2es is not None and r.v_nadir is not None and len(_t_sys):
            add_draggable_dot(
                plot_bp, r.t_S2es, _t_sys, _v_sys, _PII, _cb("t_S2es"),
                t_min=r.t_S1e, t_max=r.t_S3s,
            )
        elif r.t_S2es and r.v_nadir is not None:
            add_dot(plot_bp, r.t_S2es, r.v_nadir, _PII)

        # Point #6 S2late max — draggable on BP
        if r.t_S2lmax is not None and r.v_S2lmax is not None and len(_t_sys):
            add_draggable_dot(
                plot_bp, r.t_S2lmax, _t_sys, _v_sys, _PI, _cb("t_S2lmax"),
                t_min=r.t_S2es, t_max=r.t_S3s,
            )
        else:
            add_dot(plot_bp, r.t_S2lmax, r.v_S2lmax, _PI)

        # Point #7 S3 start (strain release) — static vlines on all 3 panels
        for p in (plot_bp, plot_hr, plot_pa):
            add_vline(p, r.t_S3s, _PIII, width=2)

        # Point #8 S3 min (PRT anchor) — draggable on BP
        if r.t_S3e is not None and r.v_S3min is not None and len(_t_sys):
            add_draggable_dot(
                plot_bp, r.t_S3e, _t_sys, _v_sys, _PIII, _cb("t_S3e"),
                t_min=r.t_S3s,
            )
        elif r.t_S3e and r.v_S3min is not None:
            add_dot(plot_bp, r.t_S3e, r.v_S3min, _PIII)

        # B bracket: horizontal lines span nadir→S2lmax; vertical + label at midpoint
        if r.t_S2lmax and r.v_S2lmax and r.t_S2es and r.v_nadir is not None and r.B is not None:
            t_b = (r.t_S2es + r.t_S2lmax) / 2
            add_hline_seg(plot_bp, r.t_S2es, r.t_S2lmax, r.v_S2lmax, _PI)
            add_hline_seg(plot_bp, r.t_S2es, r.t_S2lmax, r.v_nadir,  _PII)
            add_vline_seg(plot_bp, t_b, r.v_nadir, r.v_S2lmax, _PIII, _DashLine)
            add_label(plot_bp, t_b, r.v_S2lmax,
                      f"B={r.B:.0f}", _PIII, anchor=(0.5, 1.0))

        # Point #10 SBP overshoot — draggable on BP
        if r.t_ov is not None and r.v_ov is not None and len(_t_sys):
            add_draggable_dot(
                plot_bp, r.t_ov, _t_sys, _v_sys, _PIV, _cb("t_ov"),
                t_min=r.t_S3e, t_max=r.t_S4e,
            )
        else:
            add_dot(plot_bp, r.t_ov, r.v_ov, _PIV)
        if r.t_ov and r.v_ov:
            add_label(plot_bp, r.t_ov, r.v_ov, "SBP\nOvershoot", _PIV, anchor=(0.5, 1.0), dy=2)

        # Point #11 HR max — draggable on HR panel
        if r.hr_max_t is not None and r.hr_max_v is not None and len(_t_hr):
            add_draggable_dot(
                plot_hr, r.hr_max_t, _t_hr, _v_hr, _PIII, _cb("hr_max_t"),
                t_min=r.t_S2es, t_max=(r.t_S3s + 5 if r.t_S3s else None),
            )
        else:
            add_dot(plot_hr, r.hr_max_t, r.hr_max_v, _PIII)
        if r.hr_max_t and r.hr_max_v:
            add_label(plot_hr, r.hr_max_t, r.hr_max_v,
                      f"HR max\n{r.hr_max_v:.1f}", _PIII, anchor=(0.5, 1.0), dy=1)

        # Point #12 HR min — draggable on HR panel
        if r.hr_min_t is not None and r.hr_min_v is not None and len(_t_hr):
            # Confirmed HR min
            add_draggable_dot(
                plot_hr, r.hr_min_t, _t_hr, _v_hr, _PIV, _cb("hr_min_t"),
                t_min=r.hr_max_t, t_max=r.t_S4e,
            )
            add_label(plot_hr, r.hr_min_t, r.hr_min_v,
                      f"HR min\n{r.hr_min_v:.1f}", _PIV, anchor=(0.5, 0.0), dy=-1)

        elif r.hr_max_t is not None and len(_t_hr) and on_point_override is not None:
            # PIV suppressed (calibration) but HR signal is intact — show a ghost
            # point at the algorithm's best guess so the investigator can drag to confirm.
            _search_end = r.hr_max_t + 30.0
            _mask = (_t_hr >= r.hr_max_t) & (_t_hr <= _search_end)
            if np.any(_mask):
                _i = int(np.argmin(_v_hr[_mask]))
                _t_ghost = float(_t_hr[_mask][_i])
                add_draggable_dot(
                    plot_hr, _t_ghost, _t_hr, _v_hr, _PIV, _cb("hr_min_t"),
                    t_min=r.hr_max_t, size=12, symbol="t1",
                )
                add_label(plot_hr, _t_ghost, float(_v_hr[_mask][_i]),
                          "HR min\n(drag to confirm)", _PIV,
                          anchor=(0.5, 0.0), dy=-1)

        # VR bracket — use t_S4e if available, otherwise anchor at hr_min_t
        _vr_end = r.t_S4e or r.hr_min_t
        if r.hr_max_t and r.hr_min_t and _vr_end:
            add_hline_seg(plot_hr, r.hr_max_t, _vr_end, r.hr_max_v, _PIII)
            add_hline_seg(plot_hr, r.hr_min_t, _vr_end, r.hr_min_v, _PIV)
            add_vline_seg(plot_hr, _vr_end, r.hr_min_v, r.hr_max_v, _PIV)
            if r.VR:
                add_label(plot_hr, _vr_end + 1, (r.hr_max_v + r.hr_min_v) / 2,
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

    def export(
        self,
        plot_widget: pg.GraphicsLayoutWidget,
        result: ValsalvaResult,
        output_dir: Path,
        mode: str = "auto",
    ) -> None:
        from autonomiclab.export.excel import ExcelExporter
        from autonomiclab.export.image import ImageExporter as ImgExp

        img_exp  = ImgExp()
        xls_exp  = ExcelExporter()

        png_full = output_dir / f"{output_dir.parent.name}_valsalva_plot.png"
        img_exp.export_scene(plot_widget, png_full)

        xlsx_path = xls_exp.export_valsalva(result, output_dir, mode)
        xls_exp.embed_images_valsalva(xlsx_path, png_full, None)
