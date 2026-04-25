"""Orchestrates loading a complete Finapres dataset from a folder or .nsc file."""

from __future__ import annotations

from pathlib import Path

from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal
from autonomiclab.core.markers_handler import load_markers, load_region_markers
from autonomiclab.core.models import Dataset
from autonomiclab.core.nsc_reader import NscReader
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

# Signals to load from .nsc files (short_name as returned by NscReader).
_NSC_SIGNALS = [
    "reBAP", "reSYS", "reDIA", "reMAP",
    "HR", "HR AP", "HR ECG (RR-int)", "HR ECG",
    "fiAP", "fiSYS", "fiDIA", "fiMAP",
    "IBI", "ECG I", "ECG II", "ECG III",
    "ECG aVR", "ECG aVL", "ECG aVF", "ECG C1",
    "Resp Wave", "PAirway", "PhysioCalActive",
    "SV", "CO", "LVET", "SVR",
]

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
    ("PhysioCalActive", ""),   # 0/1 flag: 1 = Finapres mid-recording calibration active
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

    def load_nsc(self, nsc_path: Path) -> Dataset:
        """Load signals from a Finapres NOVA .nsc binary file.

        Returns a Dataset with no markers or region_markers (the .nsc format
        does not carry protocol event annotations).
        """
        nsc_path = Path(nsc_path)
        log.info("Loading NSC dataset from %s", nsc_path)

        signals = {}
        with NscReader(nsc_path) as reader:
            available = set(reader.channels())
            for name in _NSC_SIGNALS:
                if name not in available:
                    log.debug("  – %s not in file", name)
                    continue
                try:
                    sig = reader.read(name)
                    if sig and len(sig.times):
                        signals[name] = sig
                        log.debug("  ✓ %s (%d samples)", name, len(sig.times))
                except Exception as exc:
                    log.warning("  ! %s failed: %s", name, exc)

        log.info("NSC dataset ready: %d signals", len(signals))
        return Dataset(
            path=nsc_path.parent,
            prefix=nsc_path.stem,
            signals=signals,
            markers=[],
            region_markers={},
        )
