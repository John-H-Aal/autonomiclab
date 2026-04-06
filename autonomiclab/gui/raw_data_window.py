"""RawDataWindow — multi-signal viewer with ECG leads, PTT, and beat markers."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from autonomiclab.gui.close_mixin import EscapeCloseMixin
from autonomiclab.core.models import Dataset
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


class RawDataWindow(EscapeCloseMixin, QDialog):
    """Raw data viewer: BP, HR, PAirway, ECG leads with checkbox panel.

    Architecture: every PlotWidget is created ONCE at init time and populated
    with data.  _rebuild_inner only changes which widgets are in the layout
    (takeAt / addWidget / show / hide).  No widget is ever created or deleted
    during a rebuild, eliminating all Qt-object lifetime races.
    """

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
        panel.setStyleSheet("background: #f5f5f5;")
        pl = QVBoxLayout()
        pl.setContentsMargins(10, 12, 10, 12)
        pl.setSpacing(4)

        pl.addWidget(QLabel("<b>Signals</b>"))
        self._group_cbs: dict[str, QCheckBox] = {}
        for grp_key, _, sigs, default_on in self._GROUPS:
            avail = any(dataset.has_signal(sk) for sk, _, _ in sigs)
            if not avail:
                continue
            cb = self._make_cb(grp_key)
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
                cb = self._make_cb(sig_name)
                cb.setChecked(sig_name in self._ECG_DEFAULT_ON)
                cb.stateChanged.connect(lambda _: self._rebuild())
                pl.addWidget(cb)
                self._ecg_cbs[sig_name] = cb

        has_ptt = dataset.has_signal("HR AP") and dataset.has_signal("HR ECG (RR-int)")
        self._ptt_cb: QCheckBox | None = None
        if has_ptt:
            pl.addSpacing(8)
            pl.addWidget(QLabel("<b>Derived</b>"))
            self._ptt_cb = self._make_cb("PTT (ms)")
            self._ptt_cb.setChecked(False)
            self._ptt_cb.stateChanged.connect(lambda _: self._rebuild())
            pl.addWidget(self._ptt_cb)

        if self._ecg_avail:
            pl.addSpacing(16)
            pl.addWidget(QLabel("<b>Signal Info</b>"))
            self._add_signal_info(pl, dataset)

        pl.addStretch()
        panel.setLayout(pl)
        outer.addWidget(panel)

        # ── permanent plot area ───────────────────────────────────────────────
        self._plot_container = QWidget()
        self._plot_container.setStyleSheet("background: #c8d8e8;")
        self._plot_layout = QVBoxLayout()
        self._plot_layout.setContentsMargins(0, 0, 0, 0)
        self._plot_layout.setSpacing(2)
        self._plot_container.setLayout(self._plot_layout)
        outer.addWidget(self._plot_container, stretch=1)

        # Create and populate all PlotWidgets once.
        # _pw_order defines display order; keys match group keys / signal names / "PTT".
        self._all_pws:  dict[str, pg.PlotWidget] = {}
        self._pw_order: list[str] = []
        self._create_all_plots(dataset)

        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(50)
        self._rebuild_timer.timeout.connect(self._do_rebuild)

        self._do_rebuild()

    # ── plot creation (called once from __init__) ─────────────────────────────

    def _create_all_plots(self, dataset: Dataset) -> None:
        """Build every PlotWidget and fill it with data. Called only once."""

        # Group plots (BP, HR, PAirway)
        for grp_key, grp_label, sigs, _ in self._GROUPS:
            if not any(dataset.has_signal(sk) for sk, _, _ in sigs):
                continue

            pw = pg.PlotWidget(title=grp_key, parent=self._plot_container)
            self._style_pw(pw)
            pw.showGrid(x=True, y=True, alpha=0.3)
            pw.setLabel("left", grp_label)
            pw.addLegend(offset=(10, 10))

            has_data = False
            for sig_key, leg_name, color in sigs:
                sig = dataset.get_signal(sig_key)
                if not sig:
                    continue
                has_data = True
                t, v = sig.times, sig.values
                if grp_key == "HR" and sig_key in ("HR ECG (RR-int)", "HR AP"):
                    pw.plot(t, v, pen=pg.mkPen(color=color, width=1.5), name=leg_name)
                    pw.plot(t, v, pen=None, symbol="o", symbolSize=4,
                            symbolPen=pg.mkPen(color, width=1),
                            symbolBrush=pg.mkBrush(color))
                else:
                    pw.plot(t, v, pen=pg.mkPen(color=color, width=1.5), name=leg_name)

            if has_data and grp_key == "BP":
                rebap = dataset.get_signal("reBAP")
                hr_ap = dataset.get_signal("HR AP")
                if rebap and hr_ap:
                    mark_y = np.interp(hr_ap.times, rebap.times, rebap.values)
                    pw.plot(hr_ap.times, mark_y, pen=None, symbol="o", symbolSize=5,
                            symbolPen=pg.mkPen("#8B0000", width=1),
                            symbolBrush=pg.mkBrush("#8B000044"))

            if has_data:
                pw.hide()
                self._all_pws[grp_key] = pw
                self._pw_order.append(grp_key)

        # ECG leads
        for sig_name, color in self._ecg_avail:
            sig = dataset.get_signal(sig_name)
            if not sig:
                continue

            pw = pg.PlotWidget(title=sig_name, parent=self._plot_container)
            self._style_pw(pw)
            pw.showGrid(x=True, y=True, alpha=0.3)
            pw.setLabel("left", "mV")
            pw.plot(sig.times, sig.values, pen=pg.mkPen(color=color, width=1))

            if len(self._rr_times):
                peak_y = np.interp(self._rr_times, sig.times, sig.values)
                pw.addItem(pg.ScatterPlotItem(
                    self._rr_times, peak_y,
                    pen=pg.mkPen("#CC0000", width=1),
                    brush=pg.mkBrush("#CC000033"),
                    size=6,
                ), ignoreBounds=True)

            if len(sig.values):
                v_min, v_max = float(sig.values.min()), float(sig.values.max())
                span = v_max - v_min if v_max != v_min else abs(v_max) * 0.1 or 1.0
                pad  = span * 0.20
                pw.setYRange(v_min - pad, v_max + pad)
                pw.getAxis("left").setTickSpacing(
                    major=round(span / 4, 4), minor=round(span / 20, 4))

            pw.hide()
            self._all_pws[sig_name] = pw
            self._pw_order.append(sig_name)

        # PTT
        hr_ap  = dataset.get_signal("HR AP")
        hr_ecg = dataset.get_signal("HR ECG (RR-int)")
        if hr_ap and hr_ecg:
            t_ap  = hr_ap.times
            t_ecg = hr_ecg.times
            ptt_ms = np.array([
                (t_ap[i] - t_ecg[int(np.argmin(np.abs(t_ecg - t_ap[i])))]) * 1000.0
                for i in range(len(t_ap))
            ])
            pw = pg.PlotWidget(title="PTT", parent=self._plot_container)
            self._style_pw(pw)
            pw.showGrid(x=True, y=True, alpha=0.3)
            pw.setLabel("left", "PTT (ms)")
            pw.plot(t_ap, ptt_ms, pen=pg.mkPen(color="#555555", width=1.5))
            pw.plot(t_ap, ptt_ms, pen=None, symbol="o", symbolSize=4,
                    symbolPen=pg.mkPen("#555555", width=1),
                    symbolBrush=pg.mkBrush("#555555"))
            pw.addItem(pg.InfiniteLine(
                pos=0, angle=0,
                pen=pg.mkPen("#aaaaaa", width=1,
                             style=pg.QtCore.Qt.PenStyle.DashLine)))
            pw.hide()
            self._all_pws["PTT"] = pw
            self._pw_order.append("PTT")

    # ── signal info panel ─────────────────────────────────────────────────────

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

    # ── checkbox styling ──────────────────────────────────────────────────────

    _CB_STYLE = """
        QCheckBox { spacing: 6px; font-size: 12px; }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 1px solid #888; border-radius: 3px; background: white;
        }
        QCheckBox::indicator:checked  { background: #2979ff; border-color: #2979ff; image: none; }
        QCheckBox::indicator:hover    { border-color: #2979ff; }
    """

    @classmethod
    def _make_cb(cls, label: str) -> QCheckBox:
        cb = QCheckBox(label)
        cb.setStyleSheet(cls._CB_STYLE)
        return cb

    # ── plot styling ──────────────────────────────────────────────────────────

    _Y_AXIS_WIDTH = 62

    @staticmethod
    def _style_pw(pw: pg.PlotWidget) -> None:
        pw.setBackground("#c8d8e8")
        pw.getViewBox().setBackgroundColor("#ffffff")
        for axis in ("left", "bottom", "top", "right"):
            pw.getAxis(axis).setPen(pg.mkPen(color="k", width=1))
        pw.getAxis("left").setWidth(RawDataWindow._Y_AXIS_WIDTH)
        pw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ── rebuild: ONLY layout manipulation, zero widget creation/deletion ───────

    def _rebuild(self) -> None:
        self._rebuild_timer.start()

    def _do_rebuild(self) -> None:
        from PyQt6 import sip
        if sip.isdeleted(self):
            return
        log.debug("_rebuild called")
        if getattr(self, "_rebuilding", False):
            self._rebuild_timer.start()
            return
        self._rebuilding = True
        try:
            self._rebuild_inner()
        except Exception:
            log.exception("_rebuild crashed")
        finally:
            self._rebuilding = False

    def _rebuild_inner(self) -> None:
        # Snapshot checkbox states as plain Python booleans.
        group_on: dict[str, bool] = {k: cb.isChecked() for k, cb in self._group_cbs.items()}
        ecg_on:   dict[str, bool] = {k: cb.isChecked() for k, cb in self._ecg_cbs.items()}
        ptt_on:   bool = bool(self._ptt_cb and self._ptt_cb.isChecked())

        # Save X range from the first currently visible plot.
        x_range = None
        for i in range(self._plot_layout.count()):
            item = self._plot_layout.itemAt(i)
            if item and item.widget():
                try:
                    x_range = item.widget().getViewBox().viewRange()[0]
                except Exception:
                    pass
                break

        # Unlink all X axes before relayout (prevents stale links to hidden plots).
        for pw in self._all_pws.values():
            try:
                pw.getViewBox().linkView(pg.ViewBox.XAxis, None)
            except Exception:
                pass

        # Remove all widgets from layout without deleting them.
        while self._plot_layout.count():
            self._plot_layout.takeAt(0)

        def _visible(key: str) -> bool:
            if key in group_on:
                return group_on[key]
            if key in ecg_on:
                return ecg_on[key]
            return key == "PTT" and ptt_on

        # Re-add visible widgets in order; hide the rest.
        visible: list[pg.PlotWidget] = []
        for key in self._pw_order:
            pw = self._all_pws.get(key)
            if pw is None:
                continue
            if _visible(key):
                self._plot_layout.addWidget(pw, stretch=1)
                pw.show()
                visible.append(pw)
            else:
                pw.hide()

        if not visible:
            return

        # Link X axes and set axis labels.
        n = len(visible)
        for i, pw in enumerate(visible):
            pw.getAxis("bottom").setStyle(showValues=(i == n - 1))
            pw.setLabel("bottom", "Time (s)" if i == n - 1 else "")
            if i > 0:
                pw.setXLink(visible[0])

        if x_range:
            visible[0].setXRange(x_range[0], x_range[1], padding=0)
