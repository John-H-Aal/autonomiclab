"""Orchestrates loading a complete Finapres dataset from a folder."""

from __future__ import annotations

from pathlib import Path

from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal
from autonomiclab.core.markers_handler import load_markers, load_region_markers
from autonomiclab.core.models import Dataset
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

# All signal names the app knows about, in load order.
_SIGNAL_NAMES: list[tuple[str, str]] = [
    ("reBAP",          "mmHg"),
    ("reSYS",          "mmHg"),
    ("reDIA",          "mmHg"),
    ("reMAP",          "mmHg"),
    ("HR",             "bpm"),
    ("HR AP",          "bpm"),
    ("HR SpO2",        "bpm"),
    ("HR ECG (RR-int)", "bpm"),
    ("PAirway",        "mmHg"),
    ("Resp Wave",      ""),
    ("HR ECG",         "bpm"),
    ("ECG I",          "mV"),
    ("ECG II",         "mV"),
    ("ECG III",        "mV"),
    ("ECG aVR",        "mV"),
    ("ECG aVL",        "mV"),
    ("ECG aVF",        "mV"),
    ("ECG C1",         "mV"),
]


class DatasetService:
    """Load a complete Finapres dataset from a folder path."""

    def load(self, folder: Path) -> Dataset:
        """Detect prefix, load all available signals and markers.

        Raises ``FileNotFoundError`` if no CSV files exist.
        Raises ``ValueError`` if the prefix cannot be determined.
        """
        folder = Path(folder)
        prefix = detect_datetime_prefix(folder)
        log.info("Loading dataset from %s (prefix: %s)", folder, prefix)

        signals = {}
        for sig_name, unit in _SIGNAL_NAMES:
            path = folder / f"{prefix} {sig_name}.csv"
            sig = load_csv_signal(path, name=sig_name, unit=unit)
            if sig:
                signals[sig_name] = sig
                log.debug("  ✓ %s (%d samples)", sig_name, len(sig.times))
            else:
                log.debug("  – %s not found", sig_name)

        markers = load_markers(folder, prefix)
        region_markers = load_region_markers(folder, prefix)

        log.info(
            "Dataset ready: %d signals, %d markers, %d regions",
            len(signals), len(markers), len(region_markers),
        )
        return Dataset(
            path=folder,
            prefix=prefix,
            signals=signals,
            markers=markers,
            region_markers=region_markers,
        )
