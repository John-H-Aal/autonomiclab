"""Load and save per-dataset manual analysis overrides."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_FILENAME = "overrides.json"


def load(dataset_path: Path) -> dict[str, dict]:
    """Return stored overrides for this dataset, or {} if none exist."""
    p = dataset_path / _FILENAME
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Could not read overrides file: %s", exc)
        return {}


def save(dataset_path: Path, overrides: dict[str, dict]) -> None:
    """Persist overrides to disk, adding a timestamp to each entry."""
    p = dataset_path / _FILENAME
    try:
        # Stamp each entry with the current time so investigators know when it was set
        stamped = {
            phase: {**data, "saved_at": datetime.now().isoformat(timespec="seconds")}
            for phase, data in overrides.items()
        }
        p.write_text(
            json.dumps(stamped, indent=2), encoding="utf-8"
        )
        log.debug("Overrides saved: %s", p)
    except Exception as exc:
        log.warning("Could not save overrides: %s", exc)
