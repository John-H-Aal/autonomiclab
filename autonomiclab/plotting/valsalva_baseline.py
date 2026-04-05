"""BaselineRegionInteractor — interactive baseline region for the Valsalva plot.

Owns the draggable LinearRegionItem on the BP panel, linked static shades on HR
and PA, the live avg_sbp line, the A bracket, and the PRT annotation.  All live
updates happen inside this class; the caller only needs to instantiate it.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pyqtgraph as pg

from autonomiclab.analysis.valsalva import ValsalvaAnalyzer, ValsalvaResult
from autonomiclab.core.models import Dataset
from autonomiclab.plotting.helpers import shade_region

_BL        = "#2e7d32"
_PII       = "#c62828"
_PIII      = "#6a1b9a"
_DashLine  = pg.QtCore.Qt.PenStyle.DashLine
_SolidLine = pg.QtCore.Qt.PenStyle.SolidLine
_BL_FILL   = (232, 244, 232, 130)


class BaselineRegionInteractor:
    """Manages all interactive baseline-region items on the Valsalva BP panel.

    Parameters
    ----------
    plot_bp, plot_hr, plot_pa:
        The three PlotItems that receive baseline shading.
    dataset:
        Source of signal arrays (reSYS used for avg_sbp recomputation).
    result:
        ValsalvaResult mutated in-place as the user drags the region.
    on_changed:
        Called with (t_bl_s, t_bl_e) whenever the region is moved.
        Pass ``None`` for a static (non-interactive) region.
    """

    def __init__(
        self,
        plot_bp: pg.PlotItem,
        plot_hr: pg.PlotItem,
        plot_pa: pg.PlotItem,
        dataset: Dataset,
        result: ValsalvaResult,
        on_changed: Optional[Callable[[float, float], None]] = None,
    ) -> None:
        self._plot_bp = plot_bp
        self._r = result
        self._on_changed = on_changed

        if result.t_bl_s is None or result.t_bl_e is None:
            return

        sys_sig = dataset.get_signal("reSYS")
        if not sys_sig:
            # No SYS signal — draw static shading only
            for p in (plot_bp, plot_hr, plot_pa):
                shade_region(p, result.t_bl_s, result.t_bl_e, _BL_FILL)
            self._add_static_vlines(plot_bp, result.t_bl_s, result.t_bl_e)
            return

        self._t_sys = np.asarray(sys_sig.times)
        self._v_sys = np.asarray(sys_sig.values)

        ri, gi, bi, ai = _BL_FILL
        _brush = pg.mkBrush(ri, gi, bi, ai + 30)

        # ── draggable region on BP ────────────────────────────────────────────
        self._region = pg.LinearRegionItem(
            values=(result.t_bl_s, result.t_bl_e),
            orientation="vertical",
            brush=_brush,
            pen=pg.mkPen(color=_BL, width=2),
            movable=True,
        )
        self._region.setHoverBrush(_brush)
        self._region.setZValue(10)
        plot_bp.addItem(self._region, ignoreBounds=True)

        # ── width label ───────────────────────────────────────────────────────
        self._width_lbl = pg.TextItem(
            f"{result.t_bl_e - result.t_bl_s:.1f} s",
            color=_BL,
            anchor=(0.5, 0.0),
        )
        self._width_lbl.setZValue(11)
        plot_bp.addItem(self._width_lbl, ignoreBounds=True)
        self._refresh_width_lbl(result.t_bl_s, result.t_bl_e)

        # ── linked static shades on HR and PA ─────────────────────────────────
        self._bl_hr = self._linked_shade(plot_hr, result.t_bl_s, result.t_bl_e, ri, gi, bi, ai)
        self._bl_pa = self._linked_shade(plot_pa, result.t_bl_s, result.t_bl_e, ri, gi, bi, ai)

        # ── avg_sbp horizontal line + boundary vlines on BP ───────────────────
        self._sbp_hline = pg.InfiniteLine(
            pos=result.avg_sbp or 0, angle=0,
            pen=pg.mkPen(color=_BL, width=1.5, style=_DashLine),
        )
        self._vline_s = pg.InfiniteLine(
            pos=result.t_bl_s, angle=90,
            pen=pg.mkPen(color=_BL, width=1.5, style=_DashLine),
        )
        self._vline_e = pg.InfiniteLine(
            pos=result.t_bl_e, angle=90,
            pen=pg.mkPen(color=_BL, width=1.5, style=_DashLine),
        )
        plot_bp.addItem(self._sbp_hline)
        plot_bp.addItem(self._vline_s)
        plot_bp.addItem(self._vline_e)

        # ── A bracket (avg_sbp → nadir) ───────────────────────────────────────
        self._a_seg: Optional[pg.PlotDataItem] = None
        self._a_lbl: Optional[pg.TextItem] = None
        if result.t_S2es and result.v_nadir is not None and result.avg_sbp and result.A is not None:
            self._a_seg = pg.PlotDataItem(
                x=[result.t_S2es, result.t_S2es],
                y=[result.v_nadir, result.avg_sbp],
                pen=pg.mkPen(color=_PII, width=2, style=_DashLine),
            )
            plot_bp.addItem(self._a_seg)
            self._a_lbl = pg.TextItem(f"A={result.A:.0f}", color=_PII, anchor=(0.5, 1.0))
            self._a_lbl.setPos(result.t_S2es, result.avg_sbp)
            plot_bp.addItem(self._a_lbl)

        # ── PRT annotation ────────────────────────────────────────────────────
        self._prt_dot = pg.ScatterPlotItem(
            x=[result.t_prt_end] if result.t_prt_end else [],
            y=[result.avg_sbp]   if result.t_prt_end else [],
            size=8, symbol="o",
            pen=pg.mkPen(_PIII, width=1.5), brush=pg.mkBrush(_PIII),
        )
        self._prt_hline = pg.PlotDataItem(
            x=[result.t_S3e, result.t_prt_end] if (result.t_S3e and result.t_prt_end) else [],
            y=[result.avg_sbp, result.avg_sbp]  if (result.t_S3e and result.t_prt_end) else [],
            pen=pg.mkPen(color=_PIII, width=2, style=_SolidLine),
        )
        self._prt_lbl = pg.TextItem(
            f"PRT={result.PRT:.1f}s" if result.PRT else "", color=_PIII, anchor=(0.5, 1.0)
        )
        if result.t_prt_end and result.t_S3e and result.avg_sbp:
            self._prt_lbl.setPos((result.t_S3e + result.t_prt_end) / 2, result.avg_sbp - 2)
        plot_bp.addItem(self._prt_dot)
        plot_bp.addItem(self._prt_hline)
        plot_bp.addItem(self._prt_lbl)

        # ── connect live callback ─────────────────────────────────────────────
        self._region.sigRegionChanged.connect(self._on_region_changed)

    # ── private helpers ───────────────────────────────────────────────────────

    def _refresh_width_lbl(self, t0: float, t1: float) -> None:
        yr = self._plot_bp.viewRange()[1]
        y_inset = yr[1] - (yr[1] - yr[0]) * 0.04
        self._width_lbl.setPos((t0 + t1) / 2, y_inset)
        self._width_lbl.setText(f"{t1 - t0:.1f} s")

    @staticmethod
    def _linked_shade(
        plot: pg.PlotItem,
        t0: float, t1: float,
        r: int, g: int, b: int, a: int,
    ) -> pg.LinearRegionItem:
        sh = pg.LinearRegionItem(
            values=(t0, t1),
            orientation="vertical",
            brush=pg.mkBrush(r, g, b, a),
            pen=pg.mkPen(None),
            movable=False,
        )
        sh.setZValue(-10)
        plot.addItem(sh)
        return sh

    @staticmethod
    def _add_static_vlines(plot: pg.PlotItem, t0: float, t1: float) -> None:
        for t in (t0, t1):
            plot.addItem(pg.InfiniteLine(
                pos=t, angle=90,
                pen=pg.mkPen(color=_BL, width=1.5, style=_DashLine),
            ))

    # ── live update ───────────────────────────────────────────────────────────

    def _on_region_changed(self) -> None:
        r = self._r
        t0, t1 = self._region.getRegion()
        r.t_bl_s, r.t_bl_e = t0, t1

        self._vline_s.setValue(t0)
        self._vline_e.setValue(t1)
        self._bl_hr.setRegion((t0, t1))
        self._bl_pa.setRegion((t0, t1))
        self._refresh_width_lbl(t0, t1)

        mask = (self._t_sys >= t0) & (self._t_sys <= t1)
        if not np.any(mask):
            return
        r.avg_sbp = float(np.mean(self._v_sys[mask]))
        self._sbp_hline.setValue(r.avg_sbp)

        # A bracket
        if r.v_nadir is not None:
            r.A = r.avg_sbp - r.v_nadir
        if self._a_seg is not None and r.t_S2es:
            self._a_seg.setData(x=[r.t_S2es, r.t_S2es], y=[r.v_nadir, r.avg_sbp])
        if self._a_lbl is not None and r.t_S2es and r.v_nadir is not None:
            self._a_lbl.setPos(r.t_S2es, r.avg_sbp)
            self._a_lbl.setText(f"A={r.A:.0f}" if r.A is not None else "")

        # PRT
        if r.t_S3e:
            r.t_prt_end, r.PRT = ValsalvaAnalyzer._compute_prt(
                self._t_sys, self._v_sys, r.t_S3e, r.avg_sbp
            )
        if r.t_prt_end and r.t_S3e:
            self._prt_dot.setData(x=[r.t_prt_end], y=[r.avg_sbp])
            self._prt_hline.setData(
                x=[r.t_S3e, r.t_prt_end], y=[r.avg_sbp, r.avg_sbp]
            )
            self._prt_lbl.setPos((r.t_S3e + r.t_prt_end) / 2, r.avg_sbp - 2)
            self._prt_lbl.setText(f"PRT={r.PRT:.1f}s" if r.PRT else "PRT")

        # BRSa
        if r.A is not None and r.B is not None and r.PRT and r.PRT > 0:
            r.BRSa = (r.A + r.B * 0.75) / r.PRT

        if self._on_changed is not None:
            self._on_changed(r.t_bl_s, r.t_bl_e)
