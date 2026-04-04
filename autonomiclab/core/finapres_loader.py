"""Load Finapres NOVA CSV files into typed Signal objects."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from autonomiclab.core.models import Signal
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


def detect_datetime_prefix(data_dir: Path) -> str:
    """Auto-detect the datetime prefix from CSV filenames.

    Finapres files are named ``<PREFIX> <SIGNAL>.csv``, e.g.
    ``2025-09-10_09.04.59 reBAP.csv``.  This function finds the prefix by
    stripping known signal suffixes from the first matching file.
    """
    csv_files = list(Path(data_dir).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    known_signals = ["Markers.csv", "HR.csv", "reBAP.csv"]

    for signal in known_signals:
        for csv_file in csv_files:
            if csv_file.name.endswith(signal):
                filename = csv_file.name
                prefix = filename.replace(f" {signal}", "").replace(
                    f"_TEST GAT {signal}", ""
                )
                if prefix and prefix != filename:
                    log.debug("Detected prefix: %s", prefix)
                    return prefix

    raise ValueError(f"Could not detect datetime prefix from {data_dir}")


def load_csv_signal(
    csv_file: Path,
    name: str = "",
    unit: str = "",
    skip_header: int = 8,
) -> Optional[Signal]:
    """Parse a semicolon-separated Finapres CSV into a Signal.

    Returns ``None`` if the file does not exist or contains no data.
    """
    times: list[float] = []
    values: list[float] = []

    try:
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f.readlines()[skip_header:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    parts = line.split(";")
                    if len(parts) >= 2:
                        times.append(float(parts[0]))
                        values.append(float(parts[1]))
                except ValueError:
                    continue
    except FileNotFoundError:
        return None

    if not times:
        return None

    signal_name = name or csv_file.stem
    return Signal(signal_name, np.array(times), np.array(values), unit)
