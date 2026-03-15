"""Main window with snap-to-trace marker placement."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QLabel, QComboBox,
    QApplication, QScrollArea
)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np

from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal
from autonomiclab.core.markers_handler import load_markers
from autonomiclab.plotting.plotter_pyqtgraph import GATPlotterPyQtGraph
from autonomiclab.config.font_loader import FontLoader


class InteractivePlotWidget(pg.GraphicsLayoutWidget):
    """GraphicsLayoutWidget with snap-to-trace functionality"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plots = []
        self.all_curves = []
        self.marker_lines = {}
        self.snap_mode = False  # Toggle between pan/zoom (False) and snap-to-trace (True)
        self.marker_callback = None  # Callback to main window when marker is placed
        # Store original scene mouse press handler
        self._original_scene_mouse_press = self.scene().mousePressEvent
        # Override scene mouse press
        self.scene().mousePressEvent = self._scene_mouse_press
    
    def _scene_mouse_press(self, ev):
        """Handle scene-level mouse press for marker placement"""
        # If not in snap mode, always use original handler for pan/zoom
        if not self.snap_mode:
            self._original_scene_mouse_press(ev)
            return
        
        button = ev.button()
        is_right = (button == 2 or (hasattr(button, 'name') and button.name == 'RightButton'))
        
        print(f"DEBUG: Scene mouse press at {ev.scenePos()}, button={button}, snap_mode=True")
        
        # In snap mode: RIGHT click = snap-to-trace, LEFT click = pan/zoom
        if not is_right:
            print(f"DEBUG: Not right click - using pan/zoom")
            self._original_scene_mouse_press(ev)
            return
        
        # RIGHT click for snap-to-trace
        scene_pos = ev.scenePos()
        print(f"DEBUG: Right click snap - scene_pos={scene_pos}, plots={len(self.plots)}, curves={len(self.all_curves)}")
        
        # Find which plot was clicked
        for i, plot in enumerate(self.plots):
            print(f"DEBUG: Checking plot {i}")
            try:
                # Convert scene position to view position for this plot
                view_pos = plot.vb.mapSceneToView(scene_pos)
                
                # Check if click is within plot bounds
                vr = plot.vb.viewRect()
                if not vr.contains(view_pos):
                    print(f"DEBUG: Click not in plot {i}")
                    continue
                
                print(f"DEBUG: Click in plot {i} at view_pos=({view_pos.x():.1f}, {view_pos.y():.1f})")
                
                # Find closest curve point
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
                        
                        # Find closest point in x
                        x_diff = np.abs(x_data - view_pos.x())
                        closest_idx = np.argmin(x_diff)
                        
                        if x_diff[closest_idx] < 20:  # Within 20 seconds
                            curve_x = x_data[closest_idx]
                            curve_y = y_data[closest_idx]
                            
                            # Calculate pixel distance
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
                
                # Remove old marker from this plot
                if id(closest_plot) in self.marker_lines:
                    try:
                        closest_plot.removeItem(self.marker_lines[id(closest_plot)])
                    except:
                        pass
                
                # Place new yellow marker line
                marker_line = pg.InfiniteLine(
                    pos=closest_x,
                    angle=90,
                    pen=pg.mkPen('y', width=2, style=pg.QtCore.Qt.PenStyle.SolidLine)
                )
                closest_plot.addItem(marker_line)
                self.marker_lines[id(closest_plot)] = marker_line
                
                # Add circle at [closest_x, closest_y]
                scatter = pg.ScatterPlotItem(
                    x=[closest_x],
                    y=[closest_y],
                    size=10,
                    pen=pg.mkPen('y', width=2),
                    brush=pg.mkBrush(None),  # Transparent fill
                    symbol='o'
                )
                closest_plot.addItem(scatter)
                
                print(f"✓ Marker placed: X={closest_x:.1f}s, Y={closest_y:.1f}")
                
                # Call callback to main window
                if self.marker_callback:
                    plot_idx = self.plots.index(closest_plot)
                    self.marker_callback(plot_idx, closest_x, closest_y)
                break
                
            except Exception as e:
                print(f"DEBUG: Error in plot {i}: {e}")
                continue
    
    def add_plot_for_tracking(self, plot):
        """Add a plot to track for snap-to-trace"""
        self.plots.append(plot)
        print(f"DEBUG: add_plot_for_tracking - plot added, total plots = {len(self.plots)}")
        # Collect curves from plot_widget._plot_curves (stored by plotter)
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
        self.region_markers = {}   # {phase_name: (t_start, t_end)} from RegionMarkers.csv
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
        
        title_label = QLabel("Markers")
        title_label.setStyleSheet(FontLoader.style('left_panel', 'title'))
        left_layout.addWidget(title_label)
        
        self.select_button = QPushButton("Select Dataset")
        self.select_button.clicked.connect(self.select_folder)
        self.select_button.setMinimumHeight(40)
        self.select_button.setStyleSheet(FontLoader.style('left_panel', 'button'))
        left_layout.addWidget(self.select_button)
        
        self.snap_toggle = QPushButton("🔄 Pan/Zoom Mode")
        self.snap_toggle.setCheckable(True)
        self.snap_toggle.setMinimumHeight(40)
        self.snap_toggle.clicked.connect(self.toggle_snap_mode)
        self.snap_toggle.setStyleSheet(FontLoader.style('left_panel', 'button'))
        left_layout.addWidget(self.snap_toggle)
        
        self.status_label = QLabel("—")
        self.status_label.setStyleSheet(FontLoader.style('left_panel', 'status'))
        left_layout.addWidget(self.status_label)
        
        # Marker lists for each subplot
        marker_lists_label = QLabel("Snap Markers:")
        marker_lists_label.setStyleSheet(FontLoader.style('left_panel', 'filter_label'))
        left_layout.addWidget(marker_lists_label)
        
        # BP markers list
        bp_label = QLabel("Plot 0 - BP:")
        bp_label.setStyleSheet("font-weight: bold; font-size: 10px; color: #FF0000;")
        left_layout.addWidget(bp_label)
        self.bp_markers_list = QTableWidget()
        self.bp_markers_list.setColumnCount(2)
        self.bp_markers_list.setHorizontalHeaderLabels(["X (s)", "Y (mmHg)"])
        self.bp_markers_list.setColumnWidth(0, 50)
        self.bp_markers_list.setColumnWidth(1, 70)
        self.bp_markers_list.setMaximumHeight(80)
        left_layout.addWidget(self.bp_markers_list)
        
        # HR markers list
        hr_label = QLabel("Plot 1 - HR:")
        hr_label.setStyleSheet("font-weight: bold; font-size: 10px; color: #8B0000;")
        left_layout.addWidget(hr_label)
        self.hr_markers_list = QTableWidget()
        self.hr_markers_list.setColumnCount(2)
        self.hr_markers_list.setHorizontalHeaderLabels(["X (s)", "Y (bpm)"])
        self.hr_markers_list.setColumnWidth(0, 50)
        self.hr_markers_list.setColumnWidth(1, 70)
        self.hr_markers_list.setMaximumHeight(80)
        left_layout.addWidget(self.hr_markers_list)
        
        # PAirway/Resp markers list
        pa_label = QLabel("Plot 2 - PAirway:")
        pa_label.setStyleSheet("font-weight: bold; font-size: 10px; color: #0078d4;")
        left_layout.addWidget(pa_label)
        self.pa_markers_list = QTableWidget()
        self.pa_markers_list.setColumnCount(2)
        self.pa_markers_list.setHorizontalHeaderLabels(["X (s)", "Y"])
        self.pa_markers_list.setColumnWidth(0, 50)
        self.pa_markers_list.setColumnWidth(1, 70)
        self.pa_markers_list.setMaximumHeight(80)
        left_layout.addWidget(self.pa_markers_list)
        
        # Clear all markers button
        self.clear_markers_btn = QPushButton("🗑️ Clear All Markers")
        self.clear_markers_btn.setMinimumHeight(35)
        self.clear_markers_btn.clicked.connect(self.clear_all_markers)
        self.clear_markers_btn.setStyleSheet(FontLoader.style('left_panel', 'button') + "\nbackground-color: #FFB3B3;")
        left_layout.addWidget(self.clear_markers_btn)
        
        filter_label = QLabel("Select Phase:")
        filter_label.setStyleSheet(FontLoader.style('left_panel', 'filter_label'))
        left_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All"])  # populated dynamically after dataset load
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
        self.markers_table.setMaximumHeight(250)
        
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
        left_layout.addWidget(self.markers_table)
        
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
        
        left_layout.addStretch()
        
        left_widget.setLayout(left_layout)
        scroll.setWidget(left_widget)
        scroll.setStyleSheet("QScrollArea { background-color: white; }")
        
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.plot_widget = InteractivePlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.marker_callback = self.add_snap_marker  # Set callback
        right_layout.addWidget(self.plot_widget)
        
        right_widget.setLayout(right_layout)
        
        main_layout.addWidget(scroll, 0)
        main_layout.addWidget(right_widget, 1)
        
        central_widget.setLayout(main_layout)
        
        self.statusBar().showMessage("Ready | Right-click to place marker | Left-click drag to pan")
    
    def init_empty_plots(self):
        """Show blank placeholder — no data loaded yet."""
        self.plot_widget.clear()
        self.plot_widget.plots = []
        self.plot_widget.all_curves = []

        plot1 = self.plot_widget.addPlot(row=0, col=0, title="Blood Pressure (Multiple Traces)")
        plot2 = self.plot_widget.addPlot(row=1, col=0, title="Heart Rate")
        plot3 = self.plot_widget.addPlot(row=2, col=0, title="Airway / Respiratory")

        plot2.setXLink(plot1)
        plot3.setXLink(plot1)

        for plot in [plot1, plot2, plot3]:
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.getAxis('left').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('bottom').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('top').setPen(pg.mkPen(color='k', width=1))
            plot.getAxis('right').setPen(pg.mkPen(color='k', width=1))

        plot1.setLabel('left', 'BP (mmHg)')
        plot2.setLabel('left', 'HR (bpm)')
        plot3.setLabel('left', 'Amplitude')
        plot3.setLabel('bottom', 'Time (s)')

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
    
    def toggle_snap_mode(self):
        """Toggle between pan/zoom and snap-to-trace modes"""
        self.plot_widget.snap_mode = not self.plot_widget.snap_mode
        
        if self.plot_widget.snap_mode:
            self.snap_toggle.setText("📍 Snap-to-Trace Mode")
            self.snap_toggle.setStyleSheet(FontLoader.style('left_panel', 'button') + "\nbackground-color: #FFE5CC;")
            self.statusBar().showMessage("Snap-to-Trace ACTIVE: Right-click to place marker | Left-click to pan")
        else:
            self.snap_toggle.setText("🔄 Pan/Zoom Mode")
            self.snap_toggle.setStyleSheet(FontLoader.style('left_panel', 'button'))
            self.statusBar().showMessage("Pan/Zoom ACTIVE: Click and drag to pan | Scroll to zoom")
        
        print(f"DEBUG: Snap mode toggled to {self.plot_widget.snap_mode}")
    
    def add_snap_marker(self, plot_index, x, y):
        """Add marker to the appropriate list based on plot index"""
        plot = self.plot_widget.plots[plot_index] if plot_index < len(self.plot_widget.plots) else None
        
        if plot:
            title = plot.titleLabel.text if hasattr(plot, 'titleLabel') else ""
            print(f"DEBUG: add_snap_marker - plot_index={plot_index}, title='{title}', x={x:.1f}, y={y:.1f}")
        
        row = None
        
        # Map based on plot title
        if plot and 'Blood Pressure' in str(title):
            print(f"DEBUG: Adding to BP list")
            row = self.bp_markers_list.rowCount()
            self.bp_markers_list.insertRow(row)
            self.bp_markers_list.setItem(row, 0, QTableWidgetItem(f"{x:.1f}"))
            self.bp_markers_list.setItem(row, 1, QTableWidgetItem(f"{y:.1f}"))
        elif plot and 'Heart Rate' in str(title):
            print(f"DEBUG: Adding to HR list")
            row = self.hr_markers_list.rowCount()
            self.hr_markers_list.insertRow(row)
            self.hr_markers_list.setItem(row, 0, QTableWidgetItem(f"{x:.1f}"))
            self.hr_markers_list.setItem(row, 1, QTableWidgetItem(f"{y:.1f}"))
        elif plot and ('Airway' in str(title) or 'Respiratory' in str(title)):
            print(f"DEBUG: Adding to PAirway list")
            row = self.pa_markers_list.rowCount()
            self.pa_markers_list.insertRow(row)
            self.pa_markers_list.setItem(row, 0, QTableWidgetItem(f"{x:.1f}"))
            self.pa_markers_list.setItem(row, 1, QTableWidgetItem(f"{y:.1f}"))
        else:
            print(f"DEBUG: Could not determine plot type from title: {title}")
    
    def clear_all_markers(self):
        """Clear all snap markers from lists and plots"""
        self.bp_markers_list.setRowCount(0)
        self.hr_markers_list.setRowCount(0)
        self.pa_markers_list.setRowCount(0)
        
        self.plot_widget.marker_lines = {}
        
        for plot in self.plot_widget.plots:
            items_to_remove = []
            for item in plot.listDataItems():
                if isinstance(item, pg.ScatterPlotItem):
                    items_to_remove.append(item)
            for item in items_to_remove:
                plot.removeItem(item)
        
        print("DEBUG: All markers cleared")
        self.statusBar().showMessage("✓ All markers cleared")
    
    def load_dataset(self):
        if not self.dataset_path or not self.dataset_path.exists():
            self.status_label.setText("❌")
            return
        
        try:
            prefix = detect_datetime_prefix(self.dataset_path)
            self.status_label.setText(f"✓")
            
            self.markers = load_markers(self.dataset_path, prefix)
            
            if not self.markers:
                self.status_label.setText("⚠")
                return
            
            self.load_signals(prefix)
            self.region_markers = self._load_region_markers(prefix)
            self._populate_phase_combo()   # build phase list from RegionMarkers.csv
            self.update_dataset_info()
            self.update_markers_table()
            self.plot_current_phase()  # render overview immediately after load
            
            self.statusBar().showMessage(f"✓ {len(self.markers)} markers loaded")
            
        except Exception as e:
            self.status_label.setText("❌")
            self.statusBar().showMessage(f"Error: {str(e)}")
    
    def load_signals(self, prefix):
        signal_names = ['reBAP', 'reSYS', 'reDIA', 'reMAP', 'HR', 'HR AP', 'HR SpO2', 'HR ECG (RR-int)', 'PAirway', 'Resp Wave']
        
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
        """Parse <prefix>_RegionMarkers.csv → dict {phase_name: (t_start, t_end)}.

        File format:
            Time(sec);RecordingMarker
            77.8564;Start Valsalva test 1
            397.8833;End Valsalva test 1
            ...
        Pairs 'Start X' with the matching 'End X' to build a time window.
        """
        path = self.dataset_path / f"{prefix}_RegionMarkers.csv"
        if not path.exists():
            # Try space-separated prefix variant
            path = self.dataset_path / f"{prefix} RegionMarkers.csv"
        if not path.exists():
            print(f"DEBUG: RegionMarkers not found at {path}")
            return {}

        regions = {}   # name → t_start pending End
        pending = {}   # name → t_start

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
                        name = label[6:].strip()   # strip "Start "
                        pending[name] = t
                    elif label.lower().startswith('end '):
                        name = label[4:].strip()   # strip "End "
                        if name in pending:
                            regions[name] = (pending.pop(name), t)
        except Exception as e:
            print(f"DEBUG: Error reading RegionMarkers: {e}")

        print(f"DEBUG: Loaded regions: {regions}")
        return regions

    def _populate_phase_combo(self):
        """Build phase list from self.region_markers (loaded from RegionMarkers.csv).
        'All' is always first, followed by regions in file order.
        """
        phases = ['All'] + list(self.region_markers.keys())

        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItems(phases)
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.blockSignals(False)

    def _phase_time_window(self, phase_name):
        """Return (t_start, t_end) for a named phase from region_markers.
        Falls back to full HR range if not found.
        """
        if phase_name in self.region_markers:
            return self.region_markers[phase_name]

        # Fallback: full HR range
        hr = self.dataset_signals.get('HR', {})
        hr_times = hr.get('times', [])
        if hr_times:
            return float(hr_times[0]), float(hr_times[-1])
        return 0.0, 1500.0

    def plot_current_phase(self):
        phase = self.filter_combo.currentText()

        # Reset plot tracking
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
                # Unknown phase type — fall back to overview with time window
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
        """Register all plots AFTER they've been created with curves"""
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

        # Determine time window for filtering
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
                continue  # skip empty-label markers (trailing CSV rows)

            # Filter by time window
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