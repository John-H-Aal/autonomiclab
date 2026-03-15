"""Main window with snap-to-trace marker placement."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QLabel, QComboBox,
    QApplication, QScrollArea, QDialog, QCheckBox
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np

from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal
from autonomiclab.core.markers_handler import load_markers
from autonomiclab.plotting.plotter_pyqtgraph import GATPlotterPyQtGraph
from autonomiclab.config.font_loader import FontLoader


# ECG lead display order: (signal_key, y_label, colour)
_ECG_LEADS = [
    ('ECG I',   'mV',       '#1a1a1a'),
    ('ECG II',  'mV',       '#1a1a1a'),
    ('ECG III', 'mV',       '#1a1a1a'),
    ('ECG aVR', 'mV',       '#1a1a1a'),
    ('ECG aVL', 'mV',       '#1a1a1a'),
    ('ECG aVF', 'mV',       '#1a1a1a'),
    ('ECG C1',  'mV',       '#1a1a1a'),
    ('HR ECG (RR-int)', 'HR (bpm)', '#003399'),
]


class RawDataWindow(QDialog):
    """Raw data viewer: BP, HR, PAirway, ECG leads with checkbox panel."""

    # Groups: (group_key, label, signals, default_on)
    # signals: list of (sig_key, legend_name, color)
    _GROUPS = [
        ('BP', 'BP (mmHg)', [
            ('reBAP', 'reBAP', '#C0C0C0'),
            ('reSYS', 'reSYS', '#FF0000'),
            ('reDIA', 'reDIA', '#00AA00'),
            ('reMAP', 'reMAP', '#0000FF'),
        ], True),
        ('HR', 'HR (bpm)', [
            ('HR AP',          'HR (AP)',        '#8B0000'),
            ('HR ECG (RR-int)','HR ECG (RR-int)','#003399'),
        ], True),
        ('PAirway', 'PAirway (mmHg)', [
            ('PAirway', 'PAirway', '#0078d4'),
        ], True),
    ]

    _ECG_LEADS = [
        ('ECG I',   '#1a1a1a'),
        ('ECG II',  '#1a1a1a'),
        ('ECG III', '#1a1a1a'),
        ('ECG aVR', '#1a1a1a'),
        ('ECG aVL', '#1a1a1a'),
        ('ECG aVF', '#1a1a1a'),
        ('ECG C1',  '#1a1a1a'),
    ]

    _ECG_DEFAULT_ON = {'ECG I', 'ECG II'}

    def __init__(self, dataset_signals: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Raw Data Viewer")
        self.showMaximized()

        self._signals = dataset_signals
        self._rr_times = np.array(
            dataset_signals.get('HR ECG (RR-int)', {}).get('times', []))

        outer = QHBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setLayout(outer)

        # ── Left panel ────────────────────────────────────────────────────────
        panel = QWidget()
        panel.setFixedWidth(210)
        panel.setStyleSheet("background:#f5f5f5;")
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(10, 12, 10, 12)
        panel_layout.setSpacing(4)

        # Group checkboxes
        panel_layout.addWidget(QLabel("<b>Signals</b>"))
        self._group_cbs = {}
        for grp_key, grp_label, sigs, default_on in self._GROUPS:
            avail = any(dataset_signals.get(sk) for sk, _, _ in sigs)
            if not avail:
                continue
            cb = QCheckBox(grp_key)
            cb.setChecked(default_on)
            cb.stateChanged.connect(self._rebuild)
            panel_layout.addWidget(cb)
            self._group_cbs[grp_key] = cb

        # ECG lead checkboxes
        self._ecg_avail = [(k, col) for k, col in self._ECG_LEADS
                           if dataset_signals.get(k)]
        if self._ecg_avail:
            panel_layout.addSpacing(8)
            panel_layout.addWidget(QLabel("<b>ECG Leads</b>"))
            self._ecg_cbs = {}
            for sig_name, color in self._ecg_avail:
                cb = QCheckBox(sig_name)
                cb.setChecked(sig_name in self._ECG_DEFAULT_ON)
                cb.stateChanged.connect(self._rebuild)
                panel_layout.addWidget(cb)
                self._ecg_cbs[sig_name] = cb

        # PTT checkbox — available if both HR AP and HR ECG (RR-int) exist
        has_ptt = bool(dataset_signals.get('HR AP')) and bool(dataset_signals.get('HR ECG (RR-int)'))
        self._ptt_cb = None
        if has_ptt:
            panel_layout.addSpacing(8)
            panel_layout.addWidget(QLabel("<b>Derived</b>"))
            self._ptt_cb = QCheckBox("PTT (ms)")
            self._ptt_cb.setChecked(False)
            self._ptt_cb.stateChanged.connect(self._rebuild)
            panel_layout.addWidget(self._ptt_cb)

        # ECG resolution/samplerate (one shared line) — at bottom
        if self._ecg_avail:
            panel_layout.addSpacing(16)
            panel_layout.addWidget(QLabel("<b>Signal Info</b>"))

            # Helper: compute Fs and Y-res for a signal key
            def _sig_info(sig_key, unit='mmHg'):
                d = dataset_signals.get(sig_key, {})
                if not d:
                    return None
                t = np.array(d.get('times', []))
                v = np.array(d.get('values', []))
                fs_txt = f"{1.0/float(np.median(np.diff(t))):.0f} Hz" if len(t) > 1 else "\u2014"
                if unit == 'mV' and len(v) > 1:
                    diffs = np.abs(np.diff(v))
                    diffs = diffs[diffs > 0]
                    res = float(np.median(diffs)) if len(diffs) else 0.0
                    res_txt = f"{res*1000:.3f} \u00b5V" if res < 1.0 else f"{res:.4f} mV"
                    return f"{res_txt} / {fs_txt}"
                return fs_txt

            # ECG (shared)
            ecg_info = _sig_info(self._ecg_avail[0][0], 'mV')
            if ecg_info:
                self._add_info_row(panel_layout, "ECG:", ecg_info)

            # BP group — use reBAP
            bp_info = _sig_info('reBAP')
            if bp_info:
                self._add_info_row(panel_layout, "BP:", bp_info)

            # PAirway
            pa_info = _sig_info('PAirway')
            if pa_info:
                self._add_info_row(panel_layout, "PAirway:", pa_info)

            # HR AP (beat-for-beat)
            hr_d = dataset_signals.get('HR AP', {})
            if hr_d:
                t = np.array(hr_d.get('times', []))
                n_beats = len(t)
                dur = float(t[-1] - t[0]) if len(t) > 1 else 0
                avg_hr = n_beats / dur * 60 if dur > 0 else 0
                self._add_info_row(panel_layout, "HR AP:", f"{n_beats} beats (~{avg_hr:.0f} bpm avg)")


        panel_layout.addStretch()
        panel.setLayout(panel_layout)
        outer.addWidget(panel)

        # ── Plot area ─────────────────────────────────────────────────────────
        self._gw = pg.GraphicsLayoutWidget()
        self._gw.setBackground('w')
        outer.addWidget(self._gw, stretch=1)

        self._rebuild()

    def _add_info_row(self, layout, name, value):
        row_w = QWidget()
        row_l = QHBoxLayout()
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(4)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size:10px;")
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size:10px; color:#333;")
        val_lbl.setWordWrap(True)
        row_l.addWidget(name_lbl)
        row_l.addWidget(val_lbl)
        row_l.addStretch()
        row_w.setLayout(row_l)
        layout.addWidget(row_w)

    def _rebuild(self):
        # Save current X range before clearing
        x_range = None
        try:
            items = list(self._gw.scene().items())
            for item in items:
                if isinstance(item, pg.PlotItem):
                    vb = item.getViewBox()
                    x_range = vb.viewRange()[0]
                    break
        except Exception:
            pass

        self._gw.clear()

        plots = []  # (plot, y_label)

        # ── Group plots (BP, HR, PAirway) ─────────────────────────────────────
        for grp_key, grp_label, sigs, _ in self._GROUPS:
            if grp_key not in self._group_cbs:
                continue
            if not self._group_cbs[grp_key].isChecked():
                continue

            row = len(plots)
            plot = self._gw.addPlot(row=row, col=0, title=grp_key)
            plot.setMinimumHeight(130)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setLabel('left', grp_label)
            plot.addLegend(offset=(10, 10))

            has_data = False
            for sig_key, leg_name, color in sigs:
                d = self._signals.get(sig_key, {})
                if not d:
                    continue
                t = np.array(d.get('times', []))
                v = np.array(d.get('values', []))
                if not len(t):
                    continue
                has_data = True
                if grp_key == 'HR' and sig_key == 'HR ECG (RR-int)':
                    plot.plot(t, v, pen=pg.mkPen(color=color, width=1.5),
                              name=leg_name)
                    plot.plot(t, v, pen=None, symbol='o', symbolSize=4,
                              symbolPen=pg.mkPen(color, width=1),
                              symbolBrush=pg.mkBrush(color))
                elif grp_key == 'HR' and sig_key == 'HR AP':
                    # Store HR AP times for reBAP markers
                    self._hr_ap_times = t
                    plot.plot(t, v, pen=pg.mkPen(color=color, width=1.5),
                              name=leg_name)
                    plot.plot(t, v, pen=None, symbol='o', symbolSize=4,
                              symbolPen=pg.mkPen(color, width=1),
                              symbolBrush=pg.mkBrush(color))
                else:
                    plot.plot(t, v, pen=pg.mkPen(color=color, width=1.5),
                              name=leg_name)

            if has_data:
                # reBAP: add prik ved hvert HR AP tidspunkt
                if grp_key == 'BP':
                    rebap = self._signals.get('reBAP', {})
                    hr_ap = self._signals.get('HR AP', {})
                    if rebap and hr_ap:
                        rb_t = np.array(rebap.get('times', []))
                        rb_v = np.array(rebap.get('values', []))
                        hr_t = np.array(hr_ap.get('times', []))
                        if len(rb_t) and len(hr_t):
                            mark_y = np.interp(hr_t, rb_t, rb_v)
                            plot.plot(hr_t, mark_y,
                                      pen=None, symbol='o', symbolSize=5,
                                      symbolPen=pg.mkPen('#8B0000', width=1),
                                      symbolBrush=pg.mkBrush('#8B000044'))
                plots.append(plot)
            else:
                self._gw.removeItem(plot)

        # ── ECG lead plots ────────────────────────────────────────────────────
        if hasattr(self, '_ecg_cbs'):
            for sig_name, color in self._ecg_avail:
                if not self._ecg_cbs[sig_name].isChecked():
                    continue
                d = self._signals.get(sig_name, {})
                t = np.array(d.get('times', []))
                v = np.array(d.get('values', []))
                if not len(t):
                    continue

                row = len(plots)
                plot = self._gw.addPlot(row=row, col=0, title=sig_name)
                plot.setMinimumHeight(120)
                plot.showGrid(x=True, y=True, alpha=0.3)
                plot.setLabel('left', 'mV')

                plot.plot(t, v, pen=pg.mkPen(color=color, width=1))

                if len(v):
                    v_min, v_max = float(v.min()), float(v.max())
                    span = v_max - v_min if v_max != v_min else abs(v_max)*0.1 or 1.0
                    pad = span * 0.20
                    plot.setYRange(v_min - pad, v_max + pad)
                    plot.getAxis('left').setTickSpacing(
                        major=round(span/4, 4), minor=round(span/20, 4))

                if len(self._rr_times):
                    peak_y = np.interp(self._rr_times, t, v)
                    plot.plot(self._rr_times, peak_y,
                              pen=None, symbol='o', symbolSize=6,
                              symbolPen=pg.mkPen('#CC0000', width=1),
                              symbolBrush=pg.mkBrush('#CC000033'))

                plots.append(plot)

        # ── PTT subplot ───────────────────────────────────────────────────────
        if self._ptt_cb and self._ptt_cb.isChecked():
            hr_ap  = self._signals.get('HR AP', {})
            hr_ecg = self._signals.get('HR ECG (RR-int)', {})
            if hr_ap and hr_ecg:
                t_ap  = np.array(hr_ap.get('times',  []))
                t_ecg = np.array(hr_ecg.get('times', []))
                if len(t_ap) and len(t_ecg):
                    # For hvert HR AP tidspunkt: find nærmeste ECG peak
                    ptt_ms = np.empty(len(t_ap))
                    for i, tap in enumerate(t_ap):
                        j = int(np.argmin(np.abs(t_ecg - tap)))
                        ptt_ms[i] = (tap - t_ecg[j]) * 1000.0

                    row = len(plots)
                    plot = self._gw.addPlot(row=row, col=0, title="PTT")
                    plot.setMinimumHeight(120)
                    plot.showGrid(x=True, y=True, alpha=0.3)
                    plot.setLabel('left', 'PTT (ms)')
                    plot.plot(t_ap, ptt_ms,
                              pen=pg.mkPen(color='#555555', width=1.5))
                    plot.plot(t_ap, ptt_ms,
                              pen=None, symbol='o', symbolSize=4,
                              symbolPen=pg.mkPen('#555555', width=1),
                              symbolBrush=pg.mkBrush('#555555'))
                    # Zero line
                    plot.addItem(pg.InfiniteLine(
                        pos=0, angle=0,
                        pen=pg.mkPen('#aaaaaa', width=1,
                                     style=pg.QtCore.Qt.PenStyle.DashLine)))
                    plots.append(plot)

        # ── Link X axes + restore range ───────────────────────────────────────
        n = len(plots)
        if n == 0:
            return

        for i, plot in enumerate(plots):
            plot.getAxis('bottom').setStyle(showValues=(i == n - 1))
            if i == n - 1:
                plot.setLabel('bottom', 'Time (s)')
            if i > 0:
                plot.setXLink(plots[0])

        if x_range:
            plots[0].setXRange(x_range[0], x_range[1], padding=0)


class InteractivePlotWidget(pg.GraphicsLayoutWidget):
    """GraphicsLayoutWidget with snap-to-trace functionality"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plots = []
        self.all_curves = []
        self.marker_lines = {}
        self.snap_mode = False
        self.marker_callback = None
        self._original_scene_mouse_press = self.scene().mousePressEvent
        self.scene().mousePressEvent = self._scene_mouse_press

    def _scene_mouse_press(self, ev):
        if not self.snap_mode:
            self._original_scene_mouse_press(ev)
            return

        button = ev.button()
        is_right = (button == 2 or (hasattr(button, 'name') and button.name == 'RightButton'))

        print(f"DEBUG: Scene mouse press at {ev.scenePos()}, button={button}, snap_mode=True")

        if not is_right:
            print(f"DEBUG: Not right click - using pan/zoom")
            self._original_scene_mouse_press(ev)
            return

        scene_pos = ev.scenePos()
        print(f"DEBUG: Right click snap - scene_pos={scene_pos}, plots={len(self.plots)}, curves={len(self.all_curves)}")

        for i, plot in enumerate(self.plots):
            print(f"DEBUG: Checking plot {i}")
            try:
                view_pos = plot.vb.mapSceneToView(scene_pos)
                vr = plot.vb.viewRect()
                if not vr.contains(view_pos):
                    print(f"DEBUG: Click not in plot {i}")
                    continue

                print(f"DEBUG: Click in plot {i} at view_pos=({view_pos.x():.1f}, {view_pos.y():.1f})")

                closest_x = view_pos.x()
                closest_y = view_pos.y()
                closest_plot = plot
                min_dist = float('inf')

                for curve_plot, curve_item in self.all_curves:
                    try:
                        curve_data = curve_item.getData()
                        if curve_data[0] is None or len(curve_data[0]) == 0:
                            continue
                        x_data = np.array(curve_data[0])
                        y_data = np.array(curve_data[1])
                        x_diff = np.abs(x_data - view_pos.x())
                        closest_idx = np.argmin(x_diff)
                        if x_diff[closest_idx] < 20:
                            curve_x = x_data[closest_idx]
                            curve_y = y_data[closest_idx]
                            scene_curve_pos = curve_plot.vb.mapViewToScene(pg.Point(curve_x, curve_y))
                            dx = scene_pos.x() - scene_curve_pos.x()
                            dy = scene_pos.y() - scene_curve_pos.y()
                            pixel_dist = (dx*dx + dy*dy) ** 0.5
                            if pixel_dist < min_dist:
                                min_dist = pixel_dist
                                closest_x = curve_x
                                closest_y = curve_y
                                closest_plot = curve_plot
                    except Exception as e:
                        print(f"DEBUG: Error checking curve: {e}")
                        continue

                print(f"DEBUG: Found closest at X={closest_x:.1f}s, Y={closest_y:.1f}, dist={min_dist:.1f}px")

                if id(closest_plot) in self.marker_lines:
                    try:
                        closest_plot.removeItem(self.marker_lines[id(closest_plot)])
                    except:
                        pass

                marker_line = pg.InfiniteLine(
                    pos=closest_x, angle=90,
                    pen=pg.mkPen('y', width=2, style=pg.QtCore.Qt.PenStyle.SolidLine)
                )
                closest_plot.addItem(marker_line)
                self.marker_lines[id(closest_plot)] = marker_line

                scatter = pg.ScatterPlotItem(
                    x=[closest_x], y=[closest_y], size=10,
                    pen=pg.mkPen('y', width=2),
                    brush=pg.mkBrush(None), symbol='o'
                )
                closest_plot.addItem(scatter)

                print(f"✓ Marker placed: X={closest_x:.1f}s, Y={closest_y:.1f}")

                if self.marker_callback:
                    plot_idx = self.plots.index(closest_plot)
                    self.marker_callback(plot_idx, closest_x, closest_y)
                break

            except Exception as e:
                print(f"DEBUG: Error in plot {i}: {e}")
                continue

    def add_plot_for_tracking(self, plot):
        self.plots.append(plot)
        print(f"DEBUG: add_plot_for_tracking - plot added, total plots = {len(self.plots)}")
        plot_id = id(plot)
        if hasattr(self, '_plot_curves') and plot_id in self._plot_curves:
            for curve in self._plot_curves[plot_id]:
                self.all_curves.append((plot, curve))
                print(f"DEBUG: add_plot_for_tracking - curve added, total curves = {len(self.all_curves)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutonomicLab - GAT Protocol Analysis")
        self.showMaximized()

        FontLoader.load()

        self.dataset_path = None
        self.markers = []
        self.dataset_signals = {}
        self.region_markers = {}
        self.current_phase = "All"

        self.init_ui()
        self.init_empty_plots()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(380)

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        self.select_button = QPushButton("Select Dataset")
        self.select_button.clicked.connect(self.select_folder)
        self.select_button.setMinimumHeight(40)
        self.select_button.setStyleSheet(FontLoader.style('left_panel', 'button'))
        left_layout.addWidget(self.select_button)

        self.ecg_button = QPushButton("View Raw Data")
        self.ecg_button.setMinimumHeight(36)
        self.ecg_button.setEnabled(False)
        self.ecg_button.clicked.connect(self.show_ecg_window)
        self.ecg_button.setStyleSheet(FontLoader.style('left_panel', 'button'))
        left_layout.addWidget(self.ecg_button)

        self.status_label = QLabel("—")
        self.status_label.setStyleSheet(FontLoader.style('left_panel', 'status'))
        left_layout.addWidget(self.status_label)

        filter_label = QLabel("Select Phase:")
        filter_label.setStyleSheet(FontLoader.style('left_panel', 'filter_label'))
        left_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All"])
        self.filter_combo.currentTextChanged.connect(self.on_phase_changed)

        font = FontLoader.get('left_panel', 'filter_combo')
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: {font['size']}px;
                font-weight: {font['weight']};
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                min-height: 28px;
            }}
            QComboBox QAbstractItemView {{
                font-size: {font['size']}px;
                padding: 5px;
                selection-background-color: #0078d4;
            }}
        """)
        left_layout.addWidget(self.filter_combo)

        markers_label = QLabel("Markers:")
        markers_label.setStyleSheet(FontLoader.style('left_panel', 'filter_label'))
        left_layout.addWidget(markers_label)

        self.markers_table = QTableWidget()
        self.markers_table.setColumnCount(3)
        self.markers_table.setHorizontalHeaderLabels(["T(s)", "Phase", "Label"])
        self.markers_table.setColumnWidth(0, 50)
        self.markers_table.setColumnWidth(1, 60)
        self.markers_table.setColumnWidth(2, 100)
        self.markers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        header_font = FontLoader.get('left_panel', 'table_header')
        content_font = FontLoader.get('left_panel', 'table_content')
        self.markers_table.setStyleSheet(f"""
            QTableWidget {{
                font-size: {content_font['size']}px;
                font-weight: {content_font['weight']};
                gridline-color: #e0e0e0;
            }}
            QHeaderView::section {{
                font-size: {header_font['size']}px;
                font-weight: {header_font['weight']};
                padding: 4px;
                background-color: #f0f0f0;
                border: 1px solid #ddd;
            }}
        """)
        left_layout.addWidget(self.markers_table, stretch=1)

        info_label = QLabel("Dataset Info:")
        info_label.setStyleSheet(FontLoader.style('left_panel', 'filter_label'))
        left_layout.addWidget(info_label)

        self.info_label = QLabel("—")
        info_font = FontLoader.get('left_panel', 'info_box')
        self.info_label.setStyleSheet(f"""
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 3px;
            font-size: {info_font['size']}px;
            font-weight: {info_font['weight']};
        """)
        self.info_label.setWordWrap(True)
        left_layout.addWidget(self.info_label)

        left_widget.setLayout(left_layout)
        scroll.setWidget(left_widget)
        scroll.setStyleSheet("QScrollArea { background-color: white; }")

        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.plot_widget = InteractivePlotWidget()
        self.plot_widget.setBackground('w')
        right_layout.addWidget(self.plot_widget)

        right_widget.setLayout(right_layout)

        main_layout.addWidget(scroll, 0)
        main_layout.addWidget(right_widget, 1)

        central_widget.setLayout(main_layout)

        self.statusBar().showMessage("Ready | Select a dataset to begin")

    def init_empty_plots(self):
        """Show blank placeholder — no data loaded yet."""
        self.plot_widget.clear()
        self.plot_widget.plots = []
        self.plot_widget.all_curves = []

        plot1 = self.plot_widget.addPlot(row=0, col=0, title="Blood Pressure (Multiple Traces)")
        plot2 = self.plot_widget.addPlot(row=1, col=0, title="Heart Rate")
        plot3 = self.plot_widget.addPlot(row=2, col=0, title="Airway")

        plot2.setXLink(plot1)
        plot3.setXLink(plot1)

        for plot in [plot1, plot2, plot3]:
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.getAxis('left').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('bottom').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('top').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('right').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('left').setStyle(showValues=False)
            plot.getAxis('bottom').setStyle(showValues=False)

        plot1.setLabel('left', 'BP (mmHg)')
        plot1.setYRange(60, 140)
        plot2.setLabel('left', 'HR (bpm)')
        plot2.setYRange(50, 100)
        plot3.setLabel('left', 'PAirway (mmHg)')
        plot3.setYRange(0, 50)
        plot3.setLabel('bottom', 'Time (s)')
        plot1.setXRange(0, 800)

    def select_folder(self):
        default_path = Path.home() / "Projects" / "Python" / "Finapres" / "Files"

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Finapres Dataset",
            str(default_path),
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.dataset_path = Path(folder)
            self.load_dataset()

    def show_ecg_window(self):
        self._ecg_win = RawDataWindow(self.dataset_signals, parent=self)
        self._ecg_win.show()

    def load_dataset(self):
        if not self.dataset_path or not self.dataset_path.exists():
            self.status_label.setText("❌")
            return

        try:
            self.dataset_signals = {}
            prefix = detect_datetime_prefix(self.dataset_path)
            self.status_label.setText("✓")

            self.markers = load_markers(self.dataset_path, prefix)

            if not self.markers:
                self.status_label.setText("⚠")
                return

            self.load_signals(prefix)
            self.region_markers = self._load_region_markers(prefix)
            self._populate_phase_combo()
            self.current_phase = "All"
            self.update_dataset_info()
            self.update_markers_table()
            self.plot_current_phase()
            has_ecg = any(self.dataset_signals.get(k) for k in
                          ['HR ECG (RR-int)', 'ECG I', 'ECG II', 'ECG III',
                           'ECG aVR', 'ECG aVL', 'ECG aVF', 'ECG C1'])
            self.ecg_button.setEnabled(has_ecg)
            self.statusBar().showMessage(f"✓ {len(self.markers)} markers loaded")

        except Exception as e:
            self.status_label.setText("❌")
            self.statusBar().showMessage(f"Error: {str(e)}")

    def load_signals(self, prefix):
        signal_names = [
            'reBAP', 'reSYS', 'reDIA', 'reMAP',
            'HR', 'HR AP', 'HR SpO2', 'HR ECG (RR-int)',
            'PAirway', 'Resp Wave',
            'HR ECG',
            'ECG I', 'ECG II', 'ECG III',
            'ECG aVR', 'ECG aVL', 'ECG aVF',
            'ECG C1',
        ]

        for signal_name in signal_names:
            times, values = load_csv_signal(
                self.dataset_path / f"{prefix} {signal_name}.csv"
            )
            if times:
                self.dataset_signals[signal_name] = {
                    'times': times,
                    'values': values
                }

    def on_phase_changed(self):
        self.current_phase = self.filter_combo.currentText()
        self.update_markers_table()
        self.plot_current_phase()

    def _load_region_markers(self, prefix):
        path = self.dataset_path / f"{prefix}_RegionMarkers.csv"
        if not path.exists():
            path = self.dataset_path / f"{prefix} RegionMarkers.csv"
        if not path.exists():
            print(f"DEBUG: RegionMarkers not found at {path}")
            return {}

        regions = {}
        pending = {}

        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.lower().startswith('time'):
                        continue
                    parts = line.split(';', 1)
                    if len(parts) < 2:
                        continue
                    try:
                        t = float(parts[0])
                    except ValueError:
                        continue
                    label = parts[1].strip()
                    if label.lower().startswith('start '):
                        name = label[6:].strip()
                        pending[name] = t
                    elif label.lower().startswith('end '):
                        name = label[4:].strip()
                        if name in pending:
                            regions[name] = (pending.pop(name), t)
        except Exception as e:
            print(f"DEBUG: Error reading RegionMarkers: {e}")

        print(f"DEBUG: Loaded regions: {regions}")
        return regions

    def _populate_phase_combo(self):
        phases = ['All'] + list(self.region_markers.keys())

        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItems(phases)
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.blockSignals(False)

    def _phase_time_window(self, phase_name):
        if phase_name in self.region_markers:
            return self.region_markers[phase_name]

        hr = self.dataset_signals.get('HR', {})
        hr_times = hr.get('times', [])
        if hr_times:
            return float(hr_times[0]), float(hr_times[-1])
        return 0.0, 1500.0

    def plot_current_phase(self):
        phase = self.current_phase

        self.plot_widget.plots = []
        self.plot_widget.all_curves = []
        self.plot_widget.marker_lines = {}

        if not self.dataset_signals:
            self.init_empty_plots()
            return

        try:
            if phase == "All":
                GATPlotterPyQtGraph.create_overview_plot(
                    self.plot_widget, self.dataset_signals, self.markers
                )
                self._register_plots()
                return

            t_start, t_end = self._phase_time_window(phase)
            phase_lower = phase.lower()

            if 'valsalva' in phase_lower:
                GATPlotterPyQtGraph.create_valsalva_plot(
                    self.plot_widget, self.dataset_signals, self.markers,
                    t_start=t_start, t_end=t_end,
                    output_dir=str(self.dataset_path)
                )
            elif 'stand' in phase_lower:
                GATPlotterPyQtGraph.create_stand_test_plot(
                    self.plot_widget, self.dataset_signals, self.markers,
                    t_start=t_start, t_end=t_end
                )
            elif 'deep' in phase_lower or 'breath' in phase_lower:
                GATPlotterPyQtGraph.create_deep_breathing_plot(
                    self.plot_widget, self.dataset_signals, self.markers,
                    t_start=t_start, t_end=t_end,
                    output_dir=str(self.dataset_path)
                )
            else:
                GATPlotterPyQtGraph.create_overview_plot(
                    self.plot_widget, self.dataset_signals, self.markers
                )

            self._register_plots()

        except Exception as e:
            self.status_label.setText("❌")
            print(f"Plot error: {e}")
            import traceback
            traceback.print_exc()

    def _register_plots(self):
        print("DEBUG: _register_plots called")
        for item in self.plot_widget.scene().items():
            if isinstance(item, pg.PlotItem):
                print(f"DEBUG: Found PlotItem, registering...")
                self.plot_widget.add_plot_for_tracking(item)
        print(f"DEBUG: Registration complete - {len(self.plot_widget.plots)} plots, {len(self.plot_widget.all_curves)} curves")

    def update_dataset_info(self):
        if not self.markers:
            return

        phases = {}
        for m in self.markers:
            phase = m.get('phase', 'Other')
            phases[phase] = phases.get(phase, 0) + 1

        info_text = f"<b>{self.dataset_path.name}</b><br><br>"
        info_text += f"<b>Markers:</b> {len(self.markers)}<br>"
        for phase in sorted(phases.keys()):
            info_text += f"• {phase}: {phases[phase]}<br>"

        self.info_label.setText(info_text)

    def update_markers_table(self):
        filter_text = self.filter_combo.currentText()
        self.markers_table.setRowCount(0)

        if filter_text == "All":
            t_start, t_end = None, None
        elif filter_text in self.region_markers:
            t_start, t_end = self.region_markers[filter_text]
        else:
            t_start, t_end = None, None

        for marker in self.markers:
            t = marker.get('time', 0)
            label = marker.get('label', '').strip()

            if not label:
                continue

            if t_start is not None and not (t_start <= t <= t_end):
                continue

            row = self.markers_table.rowCount()
            self.markers_table.insertRow(row)
            self.markers_table.setItem(row, 0, QTableWidgetItem(f"{t:.1f}"))
            self.markers_table.setItem(row, 1, QTableWidgetItem(filter_text[:8]))
            self.markers_table.setItem(row, 2, QTableWidgetItem(label[:30]))


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    main()