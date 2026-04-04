"""Main application window — slim orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from autonomiclab.config.app_settings import AppSettings
from autonomiclab.config.font_loader import FontLoader
from autonomiclab.core.dataset_service import DatasetService
from autonomiclab.core.models import Dataset
from autonomiclab.gui.raw_data_window import RawDataWindow
from autonomiclab.gui.widgets.interactive_plot import InteractivePlotWidget
from autonomiclab.plotting.overview import OverviewPlotter
from autonomiclab.plotting.registry import PROTOCOL_REGISTRY, resolve_protocol
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_ECG_SIGNALS = ("HR ECG (RR-int)", "ECG I", "ECG II", "ECG III",
                "ECG aVR", "ECG aVL", "ECG aVF", "ECG C1")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutonomicLab — GAT Protocol Analysis")
        self.showMaximized()

        FontLoader.load()

        self._settings     = AppSettings()
        self._svc          = DatasetService()
        self._overview     = OverviewPlotter()
        self._dataset: Dataset | None = None

        self._init_ui()
        self._init_empty_plots()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── left panel (in scroll area) ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(380)
        scroll.setStyleSheet("QScrollArea { background-color: white; }")

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        self.select_button = QPushButton("Select Dataset")
        self.select_button.clicked.connect(self._select_folder)
        self.select_button.setMinimumHeight(40)
        self.select_button.setStyleSheet(FontLoader.style("left_panel", "button"))
        left_layout.addWidget(self.select_button)

        self.ecg_button = QPushButton("View Raw Data")
        self.ecg_button.setMinimumHeight(36)
        self.ecg_button.setEnabled(False)
        self.ecg_button.clicked.connect(self._show_raw_data)
        self.ecg_button.setStyleSheet(FontLoader.style("left_panel", "button"))
        left_layout.addWidget(self.ecg_button)

        self.status_label = QLabel("—")
        self.status_label.setStyleSheet(FontLoader.style("left_panel", "status"))
        left_layout.addWidget(self.status_label)

        filter_label = QLabel("Select Phase:")
        filter_label.setStyleSheet(FontLoader.style("left_panel", "filter_label"))
        left_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All"])
        self.filter_combo.currentTextChanged.connect(self._on_phase_changed)
        font = FontLoader.get("left_panel", "filter_combo")
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
        markers_label.setStyleSheet(FontLoader.style("left_panel", "filter_label"))
        left_layout.addWidget(markers_label)

        self.markers_table = QTableWidget()
        self.markers_table.setColumnCount(3)
        self.markers_table.setHorizontalHeaderLabels(["T(s)", "Phase", "Label"])
        self.markers_table.setColumnWidth(0, 50)
        self.markers_table.setColumnWidth(1, 60)
        self.markers_table.setColumnWidth(2, 100)
        self.markers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        hf = FontLoader.get("left_panel", "table_header")
        cf = FontLoader.get("left_panel", "table_content")
        self.markers_table.setStyleSheet(f"""
            QTableWidget {{
                font-size: {cf['size']}px; font-weight: {cf['weight']};
                gridline-color: #e0e0e0;
            }}
            QHeaderView::section {{
                font-size: {hf['size']}px; font-weight: {hf['weight']};
                padding: 4px; background-color: #f0f0f0; border: 1px solid #ddd;
            }}
        """)
        left_layout.addWidget(self.markers_table, stretch=1)

        info_label = QLabel("Dataset Info:")
        info_label.setStyleSheet(FontLoader.style("left_panel", "filter_label"))
        left_layout.addWidget(info_label)

        self.info_label = QLabel("—")
        inf = FontLoader.get("left_panel", "info_box")
        self.info_label.setStyleSheet(f"""
            background-color: #f5f5f5; padding: 10px; border-radius: 3px;
            font-size: {inf['size']}px; font-weight: {inf['weight']};
        """)
        self.info_label.setWordWrap(True)
        left_layout.addWidget(self.info_label)

        left_widget.setLayout(left_layout)
        scroll.setWidget(left_widget)

        # ── right panel (plot) ────────────────────────────────────────────────
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.plot_widget = InteractivePlotWidget()
        self.plot_widget.setBackground("w")
        right_layout.addWidget(self.plot_widget)
        right_widget.setLayout(right_layout)

        main_layout.addWidget(scroll, 0)
        main_layout.addWidget(right_widget, 1)
        central.setLayout(main_layout)

        self.statusBar().showMessage("Ready  |  Select a dataset to begin")

    def _init_empty_plots(self) -> None:
        self.plot_widget.clear()
        self.plot_widget.plots = []
        self.plot_widget.all_curves = []

        plot1 = self.plot_widget.addPlot(row=0, col=0, title="Blood Pressure (Multiple Traces)")
        plot2 = self.plot_widget.addPlot(row=1, col=0, title="Heart Rate")
        plot3 = self.plot_widget.addPlot(row=2, col=0, title="Airway")
        plot2.setXLink(plot1)
        plot3.setXLink(plot1)

        for plot in (plot1, plot2, plot3):
            plot.showGrid(x=True, y=True, alpha=0.3)
            for axis in ("left", "bottom", "top", "right"):
                plot.getAxis(axis).setPen(pg.mkPen(color="k", width=1))
            plot.getAxis("left").setStyle(showValues=False)
            plot.getAxis("bottom").setStyle(showValues=False)

        plot1.setLabel("left", "BP (mmHg)");   plot1.setYRange(60,  140)
        plot2.setLabel("left", "HR (bpm)");    plot2.setYRange(50,  100)
        plot3.setLabel("left", "PAirway (mmHg)"); plot3.setYRange(0, 50)
        plot3.setLabel("bottom", "Time (s)")
        plot1.setXRange(0, 800)

    # ── dataset loading ───────────────────────────────────────────────────────

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Finapres Dataset",
            str(self._settings.data_folder),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder:
            self._settings.data_folder = Path(folder)
            self._load_dataset(Path(folder))

    def _load_dataset(self, folder: Path) -> None:
        try:
            self._dataset = self._svc.load(folder)
        except Exception as exc:
            log.error("Failed to load dataset: %s", exc)
            self.status_label.setText("❌")
            self.statusBar().showMessage(f"Error: {exc}")
            return

        if not self._dataset.markers:
            self.status_label.setText("⚠  No markers found")
            return

        self.status_label.setText("✓")
        self._populate_phase_combo()
        self._update_dataset_info()
        self._update_markers_table()
        self._plot_current_phase()

        has_ecg = any(self._dataset.has_signal(k) for k in _ECG_SIGNALS)
        self.ecg_button.setEnabled(has_ecg)
        self.statusBar().showMessage(
            f"✓  {self._dataset.path.name}  |  {len(self._dataset.markers)} markers"
        )

    # ── phase plotting ────────────────────────────────────────────────────────

    def _on_phase_changed(self) -> None:
        self._update_markers_table()
        self._plot_current_phase()

    def _plot_current_phase(self) -> None:
        if not self._dataset:
            self._init_empty_plots()
            return

        self.plot_widget.plots = []
        self.plot_widget.all_curves = []
        self.plot_widget.marker_lines = {}

        phase = self.filter_combo.currentText()

        try:
            if phase == "All":
                self._overview.plot(self.plot_widget, self._dataset)
            else:
                t_start, t_end = self._dataset.phase_window(phase)
                protocol_key = resolve_protocol(phase)

                if protocol_key is None:
                    self._overview.plot(self.plot_widget, self._dataset)
                else:
                    handlers = PROTOCOL_REGISTRY[protocol_key]
                    result = handlers["analyzer"].analyze(
                        self._dataset, self._dataset.markers
                    )
                    handlers["plotter"].plot(
                        self.plot_widget, self._dataset, result,
                        t_start, t_end,
                        output_dir=self._dataset.path,
                    )

            self._register_plots()

        except Exception as exc:
            log.exception("Plot error: %s", exc)
            self.status_label.setText("❌")
            self.statusBar().showMessage(f"Plot error: {exc}")

    def _register_plots(self) -> None:
        for item in self.plot_widget.scene().items():
            if isinstance(item, pg.PlotItem):
                self.plot_widget.add_plot_for_tracking(item)
        log.debug(
            "Registered %d plots, %d curves",
            len(self.plot_widget.plots), len(self.plot_widget.all_curves),
        )

    # ── sidebar helpers ───────────────────────────────────────────────────────

    def _populate_phase_combo(self) -> None:
        phases = ["All"]
        if self._dataset:
            phases += list(self._dataset.region_markers.keys())
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItems(phases)
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.blockSignals(False)

    def _update_dataset_info(self) -> None:
        if not self._dataset:
            return
        phase_counts: dict[str, int] = {}
        for m in self._dataset.markers:
            phase_counts[m.phase] = phase_counts.get(m.phase, 0) + 1
        text = f"<b>{self._dataset.path.name}</b><br><br>"
        text += f"<b>Markers:</b> {len(self._dataset.markers)}<br>"
        for phase in sorted(phase_counts):
            text += f"• {phase}: {phase_counts[phase]}<br>"
        self.info_label.setText(text)

    def _update_markers_table(self) -> None:
        self.markers_table.setRowCount(0)
        if not self._dataset:
            return

        filter_text = self.filter_combo.currentText()
        if filter_text == "All":
            t_start, t_end = None, None
        elif filter_text in self._dataset.region_markers:
            t_start, t_end = self._dataset.region_markers[filter_text]
        else:
            t_start, t_end = None, None

        for m in self._dataset.markers:
            if not m.label.strip():
                continue
            if t_start is not None and not (t_start <= m.time <= t_end):
                continue
            row = self.markers_table.rowCount()
            self.markers_table.insertRow(row)
            self.markers_table.setItem(row, 0, QTableWidgetItem(f"{m.time:.1f}"))
            self.markers_table.setItem(row, 1, QTableWidgetItem(filter_text[:8]))
            self.markers_table.setItem(row, 2, QTableWidgetItem(m.label[:30]))

    # ── raw data window ───────────────────────────────────────────────────────

    def _show_raw_data(self) -> None:
        if self._dataset:
            self._raw_win = RawDataWindow(self._dataset, parent=self)
            self._raw_win.show()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
