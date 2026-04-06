"""RawDataWindow — multi-signal viewer with ECG leads, PTT, and beat markers."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from autonomiclab.gui.close_mixin import EscapeCloseMixin
from autonomiclab.core.models import Dataset
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


class RawDataWindow(EscapeCloseMixin, QDialog):
    """Raw data viewer: BP, HR, PAirway, ECG leads with checkbox panel."""

    _GROUPS = [
        ("BP", "BP (mmHg)", [
            ("reBAP", "reBAP", "#C0C0C0"),
            ("reSYS", "reSYS", "#FF0000"),
            ("reDIA", "reDIA", "#00AA00"),
            ("reMAP", "reMAP", "#0000FF"),
        ], True),
        ("HR", "HR (bpm)", [
            ("HR AP",           "HR (AP)",         "#8B0000"),
            ("HR ECG (RR-int)", "HR ECG (RR-int)", "#003399"),
        ], True),
        ("PAirway", "PAirway (mmHg)", [
            ("PAirway", "PAirway", "#0078d4"),
        ], True),
    ]

    _ECG_LEADS = [
        ("ECG I",   "#1a1a1a"),
        ("ECG II",  "#1a1a1a"),
        ("ECG III", "#1a1a1a"),
        ("ECG aVR", "#1a1a1a"),
        ("ECG aVL", "#1a1a1a"),
        ("ECG aVF", "#1a1a1a"),
        ("ECG C1",  "#1a1a1a"),
    ]

    _ECG_DEFAULT_ON = {"ECG I", "ECG II"}

    def __init__(self, dataset: Dataset, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raw Data Viewer")
        self.showMaximized()

        # QShortcut with WindowShortcut context fires even when a child widget
        # (e.g. pyqtgraph ViewBox) has keyboard focus, unlike keyPressEvent.
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.setContext(Qt.ShortcutContext.WindowShortcut)
        esc.activated.connect(self.close)

        self._dataset = dataset
        rr = dataset.get_signal("HR ECG (RR-int)")
        self._rr_times = rr.times if rr else np.array([])

        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setLayout(outer)

        # ── left panel ────────────────────────────────────────────────────────
        panel = QWidget()
        panel.setFixedWidth(210)
        panel.setStyleSheet("""
            background: #f5f5f5;
            QCheckBox {
                spacing: 6px;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #888;
                border-radius: 3px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #2979ff;
                border-color: #2979ff;
                image: none;
            }
            QCheckBox::indicator:hover {
                border-color: #2979ff;
            }
        """)
        pl = QVBoxLayout()
        pl.setContentsMargins(10, 12, 10, 12)
        pl.setSpacing(4)

        pl.addWidget(QLabel("<b>Signals</b>"))
        self._group_cbs: dict[str, QCheckBox] = {}
        for grp_key, _, sigs, default_on in self._GROUPS:
            avail = any(dataset.has_signal(sk) for sk, _, _ in sigs)
            if not avail:
                continue
            cb = QCheckBox(grp_key)
            cb.setChecked(default_on)
            cb.stateChanged.connect(lambda _: self._rebuild())
            pl.addWidget(cb)
            self._group_cbs[grp_key] = cb

        self._ecg_avail = [(k, col) for k, col in self._ECG_LEADS if dataset.has_signal(k)]
        self._ecg_cbs: dict[str, QCheckBox] = {}
        if self._ecg_avail:
            pl.addSpacing(8)
            pl.addWidget(QLabel("<b>ECG Leads</b>"))
            for sig_name, _ in self._ecg_avail:
                cb = QCheckBox(sig_name)
                cb.setChecked(sig_name in self._ECG_DEFAULT_ON)
                cb.stateChanged.connect(lambda _: self._rebuild())
                pl.addWidget(cb)
                self._ecg_cbs[sig_name] = cb

        # PTT
        has_ptt = dataset.has_signal("HR AP") and dataset.has_signal("HR ECG (RR-int)")
        self._ptt_cb: QCheckBox | None = None
        if has_ptt:
            pl.addSpacing(8)
            pl.addWidget(QLabel("<b>Derived</b>"))
            self._ptt_cb = QCheckBox("PTT (ms)")
            self._ptt_cb.setChecked(False)
            self._ptt_cb.stateChanged.connect(lambda _: self._rebuild())
            pl.addWidget(self._ptt_cb)

        # Signal info
        if self._ecg_avail:
            pl.addSpacing(16)
            pl.addWidget(QLabel("<b>Signal Info</b>"))
            self._add_signal_info(pl, dataset)

        pl.addStretch()
        panel.setLayout(pl)
        outer.addWidget(panel)

        # ── plot area ─────────────────────────────────────────────────────────
        self._gw = pg.GraphicsLayoutWidget()
        self._gw.setBackground("#c8d8e8")
        outer.addWidget(self._gw, stretch=1)

        self._rebuild()

    def _add_signal_info(self, layout: QVBoxLayout, dataset: Dataset) -> None:
        def _sig_info(sig_name: str, unit: str = "mmHg") -> str | None:
            sig = dataset.get_signal(sig_name)
            if not sig:
                return None
            t, v = sig.times, sig.values
            fs_txt = f"{1.0 / float(np.median(np.diff(t))):.0f} Hz" if len(t) > 1 else "—"
            if unit == "mV" and len(v) > 1:
                diffs = np.abs(np.diff(v))
                diffs = diffs[diffs > 0]
                res = float(np.median(diffs)) if len(diffs) else 0.0
                res_txt = f"{res * 1000:.3f} µV" if res < 1.0 else f"{res:.4f} mV"
                return f"{res_txt} / {fs_txt}"
            return fs_txt

        for lbl, sig_name, unit in [
            ("ECG:",      self._ecg_avail[0][0], "mV"),
            ("BP:",       "reBAP",               "mmHg"),
            ("PAirway:",  "PAirway",             "mmHg"),
        ]:
            info = _sig_info(sig_name, unit)
            if info:
                self._add_info_row(layout, lbl, info)

        hr_ap = dataset.get_signal("HR AP")
        if hr_ap:
            n = len(hr_ap.times)
            dur = hr_ap.t_end - hr_ap.t_start
            avg = n / dur * 60 if dur > 0 else 0
            self._add_info_row(layout, "HR AP:", f"{n} beats (~{avg:.0f} bpm avg)")

    @staticmethod
    def _add_info_row(layout: QVBoxLayout, name: str, value: str) -> None:
        row_w = QWidget()
        row_l = QHBoxLayout()
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(4)
        n_lbl = QLabel(name);  n_lbl.setStyleSheet("font-size:10px;")
        v_lbl = QLabel(value); v_lbl.setStyleSheet("font-size:10px; color:#333;")
        v_lbl.setWordWrap(True)
        row_l.addWidget(n_lbl)
        row_l.addWidget(v_lbl)
        row_l.addStretch()
        row_w.setLayout(row_l)
        layout.addWidget(row_w)

    # ── plot rebuild ──────────────────────────────────────────────────────────

    _Y_AXIS_WIDTH = 62  # px — fixed so all plot areas align vertically

    @staticmethod
    def _style(plot: pg.PlotItem) -> None:
        plot.getViewBox().setBackgroundColor("#ffffff")
        for axis in ("left", "bottom", "top", "right"):
            plot.getAxis(axis).setPen(pg.mkPen(color="k", width=1))
        plot.getAxis("left").setWidth(RawDataWindow._Y_AXIS_WIDTH)

    def _rebuild(self) -> None:
        log.debug("_rebuild called")
        try:
            self._rebuild_inner()
        except Exception:
            log.exception("_rebuild crashed")

    def _rebuild_inner(self) -> None:
        # Save current X range
        x_range = None
        try:
            for item in self._gw.scene().items():
                if isinstance(item, pg.PlotItem):
                    x_range = item.getViewBox().viewRange()[0]
                    break
        except Exception:
            pass

        self._gw.clear()
        plots: list[pg.PlotItem] = []

        # ── group plots ───────────────────────────────────────────────────────
        for grp_key, grp_label, sigs, _ in self._GROUPS:
            if grp_key not in self._group_cbs:
                continue
            if not self._group_cbs[grp_key].isChecked():
                continue

            row = len(plots)
            plot = self._gw.addPlot(row=row, col=0, title=grp_key)
            self._style(plot)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel("left", grp_label)
            plot.addLegend(offset=(10, 10))

            has_data = False
            for sig_key, leg_name, color in sigs:
                sig = self._dataset.get_signal(sig_key)
                if not sig:
                    continue
                has_data = True
                t, v = sig.times, sig.values
                if grp_key == "HR" and sig_key in ("HR ECG (RR-int)", "HR AP"):
                    plot.plot(t, v, pen=pg.mkPen(color=color, width=1.5), name=leg_name)
                    plot.plot(t, v, pen=None, symbol="o", symbolSize=4,
                              symbolPen=pg.mkPen(color, width=1),
                              symbolBrush=pg.mkBrush(color))
                else:
                    plot.plot(t, v, pen=pg.mkPen(color=color, width=1.5), name=leg_name)

            if has_data:
                if grp_key == "BP":
                    rebap = self._dataset.get_signal("reBAP")
                    hr_ap = self._dataset.get_signal("HR AP")
                    if rebap and hr_ap:
                        mark_y = np.interp(hr_ap.times, rebap.times, rebap.values)
                        plot.plot(hr_ap.times, mark_y, pen=None, symbol="o", symbolSize=5,
                                  symbolPen=pg.mkPen("#8B0000", width=1),
                                  symbolBrush=pg.mkBrush("#8B000044"))
                plots.append(plot)
            else:
                self._gw.removeItem(plot)

        # ── ECG leads ─────────────────────────────────────────────────────────
        for sig_name, color in self._ecg_avail:
            if not self._ecg_cbs.get(sig_name, QCheckBox()).isChecked():
                continue
            sig = self._dataset.get_signal(sig_name)
            if not sig:
                continue

            row = len(plots)
            plot = self._gw.addPlot(row=row, col=0, title=sig_name)
            self._style(plot)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel("left", "mV")
            plot.plot(sig.times, sig.values, pen=pg.mkPen(color=color, width=1))

            if len(self._rr_times):
                peak_y = np.interp(self._rr_times, sig.times, sig.values)
                markers = pg.ScatterPlotItem(
                    self._rr_times, peak_y,
                    pen=pg.mkPen("#CC0000", width=1),
                    brush=pg.mkBrush("#CC000033"),
                    size=6,
                )
                plot.addItem(markers, ignoreBounds=True)

            if len(sig.values):
                v_min, v_max = float(sig.values.min()), float(sig.values.max())
                span = v_max - v_min if v_max != v_min else abs(v_max) * 0.1 or 1.0
                pad = span * 0.20
                plot.setYRange(v_min - pad, v_max + pad)
                plot.getAxis("left").setTickSpacing(
                    major=round(span / 4, 4), minor=round(span / 20, 4))

            plots.append(plot)

        # ── PTT ───────────────────────────────────────────────────────────────
        if self._ptt_cb and self._ptt_cb.isChecked():
            hr_ap  = self._dataset.get_signal("HR AP")
            hr_ecg = self._dataset.get_signal("HR ECG (RR-int)")
            if hr_ap and hr_ecg:
                t_ap  = hr_ap.times
                t_ecg = hr_ecg.times
                ptt_ms = np.array([(t_ap[i] - t_ecg[int(np.argmin(np.abs(t_ecg - t_ap[i])))]) * 1000.0
                                   for i in range(len(t_ap))])
                row = len(plots)
                plot = self._gw.addPlot(row=row, col=0, title="PTT")
                self._style(plot)
                plot.showGrid(x=True, y=True, alpha=0.3)
                plot.setLabel("left", "PTT (ms)")
                plot.plot(t_ap, ptt_ms, pen=pg.mkPen(color="#555555", width=1.5))
                plot.plot(t_ap, ptt_ms, pen=None, symbol="o", symbolSize=4,
                          symbolPen=pg.mkPen("#555555", width=1),
                          symbolBrush=pg.mkBrush("#555555"))
                plot.addItem(pg.InfiniteLine(
                    pos=0, angle=0,
                    pen=pg.mkPen("#aaaaaa", width=1,
                                 style=pg.QtCore.Qt.PenStyle.DashLine)))
                plots.append(plot)

        # ── link X axes + restore range ───────────────────────────────────────
        n = len(plots)
        if n == 0:
            return
        for i, plot in enumerate(plots):
            plot.getAxis("bottom").setStyle(showValues=(i == n - 1))
            if i == n - 1:
                plot.setLabel("bottom", "Time (s)")
            if i > 0:
                plot.setXLink(plots[0])
        if x_range:
            plots[0].setXRange(x_range[0], x_range[1], padding=0)
