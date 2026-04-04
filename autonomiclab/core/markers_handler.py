"""Parse Finapres NOVA marker and region-marker CSV files."""

from __future__ import annotations

from pathlib import Path

from autonomiclab.core.models import Marker
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)


def determine_phase(label: str) -> str:
    """Map a marker label to a protocol phase name."""
    lo = label.lower()
    if "vm" in lo or "valsalva" in lo:
        return "Valsalva"
    if "sm" in lo or "stand" in lo:
        return "Stand Test"
    if "dbm" in lo or "deep" in lo or "breath" in lo:
        return "Deep Breathing"
    return "Other"


def load_markers(data_dir: Path, datetime_prefix: str) -> list[Marker]:
    """Load event markers from ``<PREFIX> Markers.csv`` or ``<PREFIX>_TEST GAT Markers.csv``."""
    candidates = [
        data_dir / f"{datetime_prefix} Markers.csv",
        data_dir / f"{datetime_prefix}_TEST GAT Markers.csv",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        log.warning("Marker file not found for prefix '%s'", datetime_prefix)
        return []

    markers: list[Marker] = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.lower().startswith("time"):
                    continue
                parts = line.split(";", 1)
                if len(parts) < 2:
                    continue
                try:
                    t = float(parts[0])
                except ValueError:
                    continue
                label = parts[1].strip()
                if not label:
                    continue
                markers.append(Marker(time=t, label=label, phase=determine_phase(label)))
    except Exception as exc:
        log.error("Error reading markers from %s: %s", path, exc)

    log.info("Loaded %d markers from %s", len(markers), path.name)
    return markers


def load_region_markers(data_dir: Path, datetime_prefix: str) -> dict[str, tuple[float, float]]:
    """Load phase time windows from ``<PREFIX>_RegionMarkers.csv``.

    Returns a dict mapping region name to ``(t_start, t_end)`` in seconds.
    """
    candidates = [
        data_dir / f"{datetime_prefix}_RegionMarkers.csv",
        data_dir / f"{datetime_prefix} RegionMarkers.csv",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        log.debug("RegionMarkers not found for prefix '%s'", datetime_prefix)
        return {}

    regions: dict[str, tuple[float, float]] = {}
    pending: dict[str, float] = {}

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.lower().startswith("time"):
                    continue
                parts = line.split(";", 1)
                if len(parts) < 2:
                    continue
                try:
                    t = float(parts[0])
                except ValueError:
                    continue
                label = parts[1].strip()
                lo = label.lower()
                if lo.startswith("start "):
                    pending[label[6:].strip()] = t
                elif lo.startswith("end "):
                    name = label[4:].strip()
                    if name in pending:
                        regions[name] = (pending.pop(name), t)
    except Exception as exc:
        log.error("Error reading RegionMarkers from %s: %s", path, exc)

    log.info("Loaded %d region markers: %s", len(regions), list(regions))
    return regions
