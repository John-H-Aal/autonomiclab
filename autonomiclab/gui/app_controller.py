"""AppController — orchestration layer between GUI and domain logic.

Owns: dataset loading, phase analysis, override persistence, export.
Calls back into MainWindow only via the public UI-update methods defined
in the WindowProtocol below, keeping the import graph acyclic at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMessageBox

from autonomiclab.core import overrides as override_store
from autonomiclab.core.dataset_service import DatasetService
from autonomiclab.gui.app_state import AppState
from autonomiclab.plotting.overview import OverviewPlotter
from autonomiclab.plotting.registry import PROTOCOL_REGISTRY, resolve_protocol
from autonomiclab.utils.logger import get_logger

if TYPE_CHECKING:
    from autonomiclab.gui.main_window import MainWindow

log = get_logger(__name__)

_ECG_SIGNALS = (
    "HR ECG (RR-int)", "ECG I", "ECG II", "ECG III",
    "ECG aVR", "ECG aVL", "ECG aVF", "ECG C1",
)

_PROTOCOL_SLUG = {
    "valsalva":    "valsalva_results",
    "deep breath": "deep_breathing_results",
    "stand":       "stand_results",
}


class WindowProtocol(Protocol):
    """The subset of MainWindow that AppController is allowed to call."""

    def set_status(self, level: str, message: str) -> None: ...
    def populate_phase_combo(self) -> None: ...
    def update_dataset_info(self) -> None: ...
    def update_markers_table(self) -> None: ...
    def update_override_indicator(self, phase: str) -> None: ...
    def register_plots(self) -> None: ...
    def get_current_phase(self) -> str: ...
    def set_export_enabled(self, enabled: bool) -> None: ...
    def set_ecg_enabled(self, enabled: bool) -> None: ...
    def set_plot_stack_index(self, index: int) -> None: ...
    def show_message(self, msg: str, timeout: int = 0) -> None: ...


class AppController:
    """Orchestrates load → analyse → plot → persist → export.

    Parameters
    ----------
    state:
        Shared mutable state; also held by MainWindow.
    window:
        The MainWindow instance, accessed only through ``WindowProtocol``
        so AppController stays importable without pulling in all Qt widgets.
    plot_widget:
        The pyqtgraph GraphicsLayoutWidget used for rendering.
    """

    def __init__(
        self,
        state: AppState,
        window: WindowProtocol,
        plot_widget: pg.GraphicsLayoutWidget,
    ) -> None:
        self._state      = state
        self._w          = window
        self._plot       = plot_widget
        self._svc        = DatasetService()
        self._overview   = OverviewPlotter()

    # ── dataset loading ───────────────────────────────────────────────────────

    def load_dataset(self, folder: Path) -> None:
        try:
            self._state.dataset = self._svc.load(folder)
        except Exception as exc:
            log.error("Failed to load dataset: %s", exc)
            self._w.set_status("error", f"Load failed: {exc}")
            return

        if not self._state.dataset.markers:
            self._w.set_status("warning", "No markers found")
            return

        self._state.overrides = override_store.load(self._state.dataset.path)
        if self._state.overrides:
            log.info("Loaded %d override(s) from disk", len(self._state.overrides))

        self._w.set_status("ok", f"Loaded: {self._state.dataset.path.name}")
        self._w.populate_phase_combo()
        self._w.update_dataset_info()
        self._w.update_markers_table()
        self.plot_current_phase()

        has_ecg = any(self._state.dataset.has_signal(k) for k in _ECG_SIGNALS)
        self._w.set_ecg_enabled(has_ecg)
        self._w.set_plot_stack_index(1)
        self._w.show_message(
            f"✓  {self._state.dataset.path.name}"
            f"  |  {len(self._state.dataset.markers)} markers"
        )

    def load_nsc_file(self, nsc_path: Path) -> None:
        """Load a single .nsc binary file (no markers required)."""
        try:
            self._state.dataset = self._svc.load_nsc(nsc_path)
        except Exception as exc:
            log.error("Failed to load NSC file: %s", exc)
            self._w.set_status("error", f"Load failed: {exc}")
            return

        if not self._state.dataset.signals:
            self._w.set_status("error", "No signals could be read from the file")
            return

        self._state.overrides = override_store.load(self._state.dataset.path)

        self._w.set_status("ok", f"Loaded: {nsc_path.name}")
        self._w.populate_phase_combo()
        self._w.update_dataset_info()
        self._w.update_markers_table()
        self.plot_current_phase()

        has_ecg = any(self._state.dataset.has_signal(k) for k in _ECG_SIGNALS)
        self._w.set_ecg_enabled(has_ecg)
        self._w.set_plot_stack_index(1)
        self._w.show_message(
            f"✓  {nsc_path.name}"
            f"  |  {len(self._state.dataset.signals)} signals"
        )

    # ── phase plotting ────────────────────────────────────────────────────────

    def plot_current_phase(self) -> None:
        st = self._state
        if not st.dataset:
            return

        self._plot.plots = []
        self._plot.all_curves = []
        self._plot.marker_lines = {}

        phase = self._w.get_current_phase()

        st.last_protocol_key = None
        st.last_result       = None
        self._w.set_export_enabled(False)

        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()  # flush pending paints before clearing old plot objects
        self._plot.setUpdatesEnabled(False)
        try:
            if phase == "All":
                self._overview.plot(self._plot, st.dataset)
            else:
                t_start, t_end = st.dataset.phase_window(phase)
                protocol_key   = resolve_protocol(phase)

                if protocol_key is None:
                    self._overview.plot(self._plot, st.dataset)
                else:
                    handlers = PROTOCOL_REGISTRY[protocol_key]

                    analyze_kwargs = (
                        {"t_start": t_start, "t_end": t_end}
                        if protocol_key == "valsalva" else {}
                    )
                    result = handlers["analyzer"].analyze(
                        st.dataset, st.dataset.markers, **analyze_kwargs
                    )

                    # Apply any stored manual overrides
                    if phase in st.overrides:
                        ov = st.overrides[phase]
                        if protocol_key == "valsalva":
                            if "t_bl_s" in ov and "t_bl_e" in ov:
                                result.t_bl_s = ov["t_bl_s"]
                                result.t_bl_e = ov["t_bl_e"]
                                handlers["analyzer"].recompute_from_baseline(
                                    result, st.dataset
                                )
                            if ov.get("points"):
                                handlers["analyzer"].apply_point_overrides(
                                    result, st.dataset, ov["points"]
                                )
                        elif protocol_key == "deep breath":
                            if "cycles" in ov:
                                handlers["analyzer"].apply_cycle_overrides(
                                    result, st.dataset, ov["cycles"]
                                )
                        st.analysis_mode = "manual"
                    else:
                        st.analysis_mode = "auto"

                    # Wire interactive callbacks
                    plot_kwargs: dict = {}
                    if protocol_key == "valsalva":
                        plot_kwargs["on_manual_override"] = (
                            lambda t0, t1, p=phase: self.on_baseline_override(p, t0, t1)
                        )
                        plot_kwargs["on_point_override"] = (
                            lambda field, t, p=phase: self.on_point_override(p, field, t)
                        )
                    elif protocol_key == "deep breath":
                        plot_kwargs["on_cycle_override"] = (
                            lambda cycles, p=phase: self.on_cycle_override(p, cycles)
                        )

                    handlers["plotter"].plot(
                        self._plot, st.dataset, result,
                        t_start, t_end, **plot_kwargs,
                    )
                    st.last_protocol_key = protocol_key
                    st.last_result       = result
                    self._w.set_export_enabled(True)
                    if protocol_key in ("valsalva", "deep breath"):
                        self._w.update_override_indicator(phase)

            self._w.register_plots()

        except Exception as exc:
            log.exception("Plot error: %s", exc)
            self._w.set_status("error", f"Plot error: {exc}")
            self._w.show_message(f"Plot error: {exc}")
        finally:
            self._plot.setUpdatesEnabled(True)

    # ── override callbacks ────────────────────────────────────────────────────

    def on_baseline_override(self, phase: str, t_bl_s: float, t_bl_e: float) -> None:
        ov = self._state.overrides.setdefault(phase, {})
        ov["t_bl_s"] = t_bl_s
        ov["t_bl_e"] = t_bl_e
        self._state.analysis_mode = "manual"
        self._save_overrides()
        self._w.update_override_indicator(phase)

    def on_cycle_override(self, phase: str, cycles: list[dict]) -> None:
        ov = self._state.overrides.setdefault(phase, {})
        ov["cycles"] = cycles
        self._state.analysis_mode = "manual"
        self._save_overrides()
        self._w.update_override_indicator(phase)
        self.plot_current_phase()

    def on_point_override(self, phase: str, field: str, new_t: float) -> None:
        ov = self._state.overrides.setdefault(phase, {})
        ov.setdefault("points", {})[field] = new_t
        self._state.analysis_mode = "manual"
        self._save_overrides()
        self._w.update_override_indicator(phase)
        self.plot_current_phase()

    def reset_to_auto(self, phase: str) -> None:
        answer = QMessageBox.question(
            None,
            "Reset to Auto",
            f"Discard all manual overrides for '{phase}' and restore the algorithm result?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._state.overrides.pop(phase, None)
        self._save_overrides()
        self._state.analysis_mode = "auto"
        self._w.update_override_indicator(phase)
        self.plot_current_phase()

    # ── export ────────────────────────────────────────────────────────────────

    def export_current(self) -> None:
        st = self._state
        if not st.last_protocol_key or st.last_result is None or not st.dataset:
            return

        mode     = st.analysis_mode
        handlers = PROTOCOL_REGISTRY[st.last_protocol_key]
        results_dir = st.dataset.path / "results"
        results_dir.mkdir(exist_ok=True)

        slug     = _PROTOCOL_SLUG.get(st.last_protocol_key, st.last_protocol_key)
        existing = sorted(results_dir.glob(f"*_{slug}_*_{mode}.xlsx"))
        if existing:
            names = "\n".join(f.name for f in existing)
            answer = QMessageBox.question(
                None,
                "Export already exists",
                f"A {mode} export already exists:\n\n{names}\n\nExport again?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            self._w.set_export_enabled(False)
            QApplication.processEvents()
            handlers["plotter"].export(self._plot, st.last_result, results_dir, mode)
            self._w.set_status("ok", "Excel exported")
            self._w.show_message("Excel exported successfully")
        except Exception as exc:
            log.exception("Export error: %s", exc)
            self._w.set_status("error", f"Export error: {exc}")
            self._w.show_message(f"Export error: {exc}")
        finally:
            self._w.set_export_enabled(True)

    # ── persistence ───────────────────────────────────────────────────────────

    def _save_overrides(self) -> None:
        if not self._state.dataset:
            return
        ok = override_store.save(self._state.dataset.path, self._state.overrides)
        if not ok:
            self._w.show_message(
                "WARNING: could not save overrides to disk — check folder permissions",
                8000,
            )
