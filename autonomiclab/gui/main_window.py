"""Main application window — slim orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette  # QPalette/QColor used in _ComboDelegate
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QMessageBox, QPushButton, QSplitter, QStackedWidget,
    QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from autonomiclab.gui.close_mixin import EscapeCloseMixin
from autonomiclab.config.app_settings import AppSettings
from autonomiclab.config.font_loader import FontLoader
from autonomiclab.core.dataset_service import DatasetService
from autonomiclab.core.models import Dataset
from autonomiclab.core import overrides as override_store
from autonomiclab.gui.raw_data_window import RawDataWindow
from autonomiclab.gui.widgets.interactive_plot import InteractivePlotWidget
from autonomiclab.plotting.overview import OverviewPlotter
from autonomiclab.plotting.registry import PROTOCOL_REGISTRY, resolve_protocol
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


class _ComboDelegate(QStyledItemDelegate):
    """Force readable item colors in the phase combo on every platform."""

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        option.palette.setColor(QPalette.ColorRole.Text,            QColor("#1a1a1a"))
        option.palette.setColor(QPalette.ColorRole.Highlight,       QColor("#0060aa"))
        option.palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))


_ECG_SIGNALS = ("HR ECG (RR-int)", "ECG I", "ECG II", "ECG III",
                "ECG aVR", "ECG aVL", "ECG aVF", "ECG C1")

_PRIMARY_BTN = """
    QPushButton {{
        background-color: #0078d4;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        font-size: {size}px;
        font-weight: {weight};
    }}
    QPushButton:hover {{ background-color: #106ebe; }}
    QPushButton:pressed {{ background-color: #005a9e; }}
    QPushButton:disabled {{ background-color: #c8c8c8; color: #888; }}
"""

_SECONDARY_BTN = """
    QPushButton {{
        background-color: transparent;
        color: #0078d4;
        border: 1px solid #0078d4;
        border-radius: 4px;
        padding: 7px 16px;
        font-size: {size}px;
        font-weight: {weight};
    }}
    QPushButton:hover {{ background-color: #e8f2fc; }}
    QPushButton:pressed {{ background-color: #c7e0f4; }}
    QPushButton:disabled {{ color: #aaa; border-color: #ccc; }}
"""


class MainWindow(EscapeCloseMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutonomicLab — GAT Protocol Analysis")

        FontLoader.load()

        self._settings     = AppSettings()
        self._svc          = DatasetService()
        self._overview     = OverviewPlotter()
        self._dataset: Dataset | None = None
        self._last_protocol_key: str | None = None
        self._last_result: object | None = None
        self._overrides: dict[str, dict] = {}   # phase → {t_bl_s, t_bl_e}
        self._analysis_mode: str = "auto"

        self._init_ui()
        self._init_empty_plots()
        self.showMaximized()

    # ── UI construction ───────────────────────────────────────────────────────

    def _make_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            "font-size: 10px; font-weight: bold; color: #888; "
            "letter-spacing: 1px; padding: 4px 0 2px 0;"
        )
        return lbl

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")

        # ── left panel ────────────────────────────────────────────────────────
        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: #e8edf3;")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(6)

        left_layout.addWidget(self._make_section_header("Actions"))

        btn_font = FontLoader.get("left_panel", "button")
        self.select_button = QPushButton("Select Dataset")
        self.select_button.clicked.connect(self._select_folder)
        self.select_button.setMinimumHeight(40)
        self.select_button.setStyleSheet(
            _PRIMARY_BTN.format(size=btn_font["size"], weight=btn_font["weight"])
        )
        left_layout.addWidget(self.select_button)

        self.ecg_button = QPushButton("View Raw Data")
        self.ecg_button.setMinimumHeight(36)
        self.ecg_button.setEnabled(False)
        self.ecg_button.clicked.connect(self._show_raw_data)
        self.ecg_button.setStyleSheet(
            _SECONDARY_BTN.format(size=btn_font["size"], weight=btn_font["weight"])
        )
        left_layout.addWidget(self.ecg_button)

        self.status_label = QLabel("No dataset loaded")
        self.status_label.setStyleSheet(
            FontLoader.style("left_panel", "status") + " color: #888;"
        )
        left_layout.addWidget(self.status_label)

        left_layout.addSpacing(6)
        left_layout.addWidget(self._make_section_header("Phase"))

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
        """)
        self.filter_combo.view().setItemDelegate(
            _ComboDelegate(self.filter_combo.view())
        )
        left_layout.addWidget(self.filter_combo)

        self.export_button = QPushButton("Export Excel")
        self.export_button.setMinimumHeight(36)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(lambda: self._export_current())
        self.export_button.setStyleSheet(
            _SECONDARY_BTN.format(size=btn_font["size"], weight=btn_font["weight"])
        )
        left_layout.addWidget(self.export_button)

        self.reset_button = QPushButton("Reset to Auto")
        self.reset_button.setMinimumHeight(36)
        self.reset_button.setEnabled(False)
        self.reset_button.setVisible(False)
        self.reset_button.clicked.connect(lambda: self._reset_to_auto())
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b34700;
                border: 1px solid #b34700;
                border-radius: 4px;
                padding: 7px 16px;
                font-size: """ + str(btn_font["size"]) + """px;
            }
            QPushButton:hover { background-color: #fff3e0; }
            QPushButton:pressed { background-color: #ffe0b2; }
        """)
        left_layout.addWidget(self.reset_button)

        self.override_label = QLabel()
        self.override_label.setWordWrap(True)
        self.override_label.setVisible(False)
        self.override_label.setStyleSheet(
            "color: #b34700; font-size: 10px; padding: 2px 0;"
        )
        left_layout.addWidget(self.override_label)

        left_layout.addSpacing(6)
        left_layout.addWidget(self._make_section_header("Markers"))

        self.markers_table = QTableWidget()
        self.markers_table.setColumnCount(3)
        self.markers_table.setHorizontalHeaderLabels(["T(s)", "Phase", "Label"])
        self.markers_table.setColumnWidth(0, 55)
        self.markers_table.setColumnWidth(1, 65)
        hdr = self.markers_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
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

        left_layout.addSpacing(6)
        left_layout.addWidget(self._make_section_header("Dataset Info"))

        self.info_label = QLabel("—")
        inf = FontLoader.get("left_panel", "info_box")
        self.info_label.setStyleSheet(f"""
            background-color: #f0f0f0; padding: 10px; border-radius: 3px;
            font-size: {inf['size']}px; font-weight: {inf['weight']};
        """)
        self.info_label.setWordWrap(True)
        left_layout.addWidget(self.info_label)

        left_widget.setLayout(left_layout)

        # ── right panel (stacked: placeholder + plot) ─────────────────────────
        self._plot_stack = QStackedWidget()

        placeholder = QWidget()
        placeholder.setStyleSheet("background-color: #c8d8e8;")
        ph_layout = QVBoxLayout()
        ph_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_font = FontLoader.get("plot_panel", "placeholder")
        ph_label = QLabel("Select a dataset to begin")
        ph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_label.setStyleSheet(f"font-size: {ph_font['size']}px; color: #aaa;")
        ph_layout.addWidget(ph_label)
        placeholder.setLayout(ph_layout)
        self._plot_stack.addWidget(placeholder)       # index 0

        self.plot_widget = InteractivePlotWidget()
        self.plot_widget.setBackground("#c8d8e8")
        self._plot_stack.addWidget(self.plot_widget)  # index 1
        self._plot_stack.setCurrentIndex(0)

        splitter.addWidget(left_widget)
        splitter.addWidget(self._plot_stack)

        left_pct = FontLoader.get_layout().get("left_width_percent", 15)
        splitter.setStretchFactor(0, left_pct)
        splitter.setStretchFactor(1, 100 - left_pct)
        self._splitter = splitter

        main_layout.addWidget(splitter)
        central.setLayout(main_layout)

        self.statusBar().showMessage("Ready  |  Select a dataset to begin")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        left_pct = FontLoader.get_layout().get("left_width_percent", 15)
        total = self.width()
        left_px = int(total * left_pct / 100)
        self._splitter.setSizes([left_px, total - left_px])

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

        plot1.setLabel("left", "BP (mmHg)");      plot1.setYRange(60,  140)
        plot2.setLabel("left", "HR (bpm)");       plot2.setYRange(50,  100)
        plot3.setLabel("left", "PAirway (mmHg)"); plot3.setYRange(0,   50)
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
            self._load_dataset(Path(folder))

    def _load_dataset(self, folder: Path) -> None:
        try:
            self._dataset = self._svc.load(folder)
        except Exception as exc:
            log.error("Failed to load dataset: %s", exc)
            self._set_status("error", f"Load failed: {exc}")
            return

        if not self._dataset.markers:
            self._set_status("warning", "No markers found")
            return

        # Restore any previously saved manual overrides for this dataset
        self._overrides = override_store.load(self._dataset.path)
        if self._overrides:
            log.info("Loaded %d override(s) from disk", len(self._overrides))

        self._set_status("ok", f"Loaded: {self._dataset.path.name}")
        self._populate_phase_combo()
        self._update_dataset_info()
        self._update_markers_table()
        self._plot_current_phase()

        has_ecg = any(self._dataset.has_signal(k) for k in _ECG_SIGNALS)
        self.ecg_button.setEnabled(has_ecg)
        self._plot_stack.setCurrentIndex(1)
        self.statusBar().showMessage(
            f"✓  {self._dataset.path.name}  |  {len(self._dataset.markers)} markers"
        )

    # ── status helpers ────────────────────────────────────────────────────────

    def _set_status(self, level: str, message: str) -> None:
        colors = {"ok": "#27ae60", "warning": "#e67e22", "error": "#c0392b"}
        color = colors.get(level, "#888")
        self.status_label.setStyleSheet(
            FontLoader.style("left_panel", "status") + f" color: {color};"
        )
        self.status_label.setText(message)

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

        self._last_protocol_key = None
        self._last_result = None
        self.export_button.setEnabled(False)
        self.reset_button.setVisible(False)
        self.override_label.setVisible(False)

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

                    # Pass time window so multiple sections find their own markers
                    analyze_kwargs = (
                        {"t_start": t_start, "t_end": t_end}
                        if protocol_key == "valsalva" else {}
                    )
                    result = handlers["analyzer"].analyze(
                        self._dataset, self._dataset.markers, **analyze_kwargs
                    )

                    # Restore previous manual overrides for this phase
                    if phase in self._overrides:
                        ov = self._overrides[phase]
                        if protocol_key == "valsalva":
                            if "t_bl_s" in ov and "t_bl_e" in ov:
                                result.t_bl_s = ov["t_bl_s"]
                                result.t_bl_e = ov["t_bl_e"]
                                handlers["analyzer"].recompute_from_baseline(result, self._dataset)
                            if ov.get("points"):
                                handlers["analyzer"].apply_point_overrides(
                                    result, self._dataset, ov["points"]
                                )
                        elif protocol_key == "deep breath":
                            if "cycles" in ov:  # empty list is a valid override (all deleted)
                                handlers["analyzer"].apply_cycle_overrides(
                                    result, self._dataset, ov["cycles"]
                                )
                        self._analysis_mode = "manual"
                    else:
                        self._analysis_mode = "auto"

                    plot_kwargs = {}
                    if protocol_key == "valsalva":
                        plot_kwargs["on_manual_override"] = (
                            lambda t0, t1, p=phase: self._on_baseline_override(p, t0, t1)
                        )
                        plot_kwargs["on_point_override"] = (
                            lambda field, t, p=phase: self._on_point_override(p, field, t)
                        )
                    elif protocol_key == "deep breath":
                        plot_kwargs["on_cycle_override"] = (
                            lambda cycles, p=phase: self._on_db_cycle_override(p, cycles)
                        )

                    handlers["plotter"].plot(
                        self.plot_widget, self._dataset, result,
                        t_start, t_end, **plot_kwargs,
                    )
                    self._last_protocol_key = protocol_key
                    self._last_result = result
                    self.export_button.setEnabled(True)
                    if protocol_key in ("valsalva", "deep breath"):
                        self._update_override_indicator(phase)

            self._register_plots()

        except Exception as exc:
            log.exception("Plot error: %s", exc)
            self._set_status("error", f"Plot error: {exc}")
            self.statusBar().showMessage(f"Plot error: {exc}")

    _PROTOCOL_SLUG = {
        "valsalva":    "valsalva_results",
        "deep breath": "deep_breathing_results",
        "stand":       "stand_results",
    }

    def _on_baseline_override(self, phase: str, t_bl_s: float, t_bl_e: float) -> None:
        ov = self._overrides.setdefault(phase, {})
        ov["t_bl_s"] = t_bl_s
        ov["t_bl_e"] = t_bl_e
        self._analysis_mode = "manual"
        if self._dataset:
            override_store.save(self._dataset.path, self._overrides)
        self._update_override_indicator(phase)

    def _on_db_cycle_override(self, phase: str, cycles: list[dict]) -> None:
        """Called when investigator moves, deletes or inserts a deep-breathing cycle."""
        ov = self._overrides.setdefault(phase, {})
        ov["cycles"] = cycles
        self._analysis_mode = "manual"
        if self._dataset:
            override_store.save(self._dataset.path, self._overrides)
        self._update_override_indicator(phase)
        self._plot_current_phase()

    def _on_point_override(self, phase: str, field: str, new_t: float) -> None:
        """Called when the investigator drags a marker point to a new position."""
        ov = self._overrides.setdefault(phase, {})
        ov.setdefault("points", {})[field] = new_t
        self._analysis_mode = "manual"
        if self._dataset:
            override_store.save(self._dataset.path, self._overrides)
        self._update_override_indicator(phase)
        # Re-plot so all dependent annotations (A, B, brackets, shades) update
        self._plot_current_phase()

    def _update_override_indicator(self, phase: str) -> None:
        has_override = phase in self._overrides
        self.reset_button.setVisible(has_override)
        self.reset_button.setEnabled(has_override)
        if has_override:
            ov = self._overrides[phase]
            has_baseline = "t_bl_s" in ov or "t_bl_e" in ov
            has_points   = bool(ov.get("points"))
            has_cycles   = "cycles" in ov
            if has_cycles:
                n = len(ov["cycles"])
                what = "All RSA cycles deleted" if n == 0 else "RSA cycles manually edited"
            elif has_baseline and has_points:
                what = "Baseline + markers overridden"
            elif has_baseline:
                what = "Baseline overridden"
            else:
                n = len(ov.get("points", {}))
                what = f"{n} marker{'s' if n != 1 else ''} overridden"
            saved_at = ov.get("saved_at", "")
            date_str = f"\nSaved: {saved_at}" if saved_at else ""
            self.override_label.setText(f"Manual override active: {what}{date_str}")
            self.override_label.setVisible(True)
        else:
            self.override_label.setVisible(False)

    def _reset_to_auto(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        phase = self.filter_combo.currentText()
        answer = QMessageBox.question(
            self,
            "Reset to Auto",
            f"Discard all manual overrides for '{phase}' and restore the algorithm result?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if phase in self._overrides:
            del self._overrides[phase]
            if self._dataset:
                override_store.save(self._dataset.path, self._overrides)
        self._analysis_mode = "auto"
        self._update_override_indicator(phase)
        self._plot_current_phase()

    def _export_current(self, mode: str = "auto") -> None:
        mode = self._analysis_mode
        if not self._last_protocol_key or self._last_result is None or not self._dataset:
            return
        handlers = PROTOCOL_REGISTRY[self._last_protocol_key]
        results_dir = self._dataset.path / "results"
        results_dir.mkdir(exist_ok=True)

        slug = self._PROTOCOL_SLUG.get(self._last_protocol_key, self._last_protocol_key)
        existing = sorted(results_dir.glob(f"*_{slug}_*_{mode}.xlsx"))
        if existing:
            names = "\n".join(f.name for f in existing)
            answer = QMessageBox.question(
                self,
                "Export already exists",
                f"A {mode} export for this protocol already exists:\n\n{names}\n\nExport again?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            self.export_button.setEnabled(False)
            self.export_button.setText("Exporting…")
            QApplication.processEvents()
            handlers["plotter"].export(
                self.plot_widget, self._last_result, results_dir, mode
            )
            self._set_status("ok", "Excel exported")
            self.statusBar().showMessage("Excel exported successfully")
        except Exception as exc:
            log.exception("Export error: %s", exc)
            self._set_status("error", f"Export error: {exc}")
            self.statusBar().showMessage(f"Export error: {exc}")
        finally:
            self.export_button.setText("Export Excel")
            self.export_button.setEnabled(True)

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
            tip = f"{m.phase}  |  {m.label}  |  T = {m.time:.1f} s"
            for col, text in enumerate((f"{m.time:.1f}", m.phase[:8], m.label[:30])):
                item = QTableWidgetItem(text)
                item.setToolTip(tip)
                self.markers_table.setItem(row, col, item)

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
