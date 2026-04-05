"""Load and save per-dataset manual analysis overrides.

Design guarantees
-----------------
* **Atomic writes:** data is written to a sibling ``.tmp`` file and then
  renamed into place.  On POSIX the rename is atomic; on Windows it is
  near-atomic (os.replace).  A crash mid-write leaves the previous file
  intact rather than a half-written one.
* **Schema validation on load:** malformed or hand-edited files are
  rejected with a warning rather than causing a KeyError later.
* **Save returns a bool** so callers can detect and surface failures.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_FILENAME = "overrides.json"


# ── schema ────────────────────────────────────────────────────────────────────

def _validate(data: object) -> dict[str, dict]:
    """Raise ValueError if *data* does not look like a valid overrides dict."""
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object at the top level, got {type(data).__name__}")
    for phase, entry in data.items():
        if not isinstance(phase, str):
            raise ValueError(f"Phase key must be a string, got {type(phase).__name__}")
        if not isinstance(entry, dict):
            raise ValueError(f"Entry for phase {phase!r} must be a JSON object")
        for float_key in ("t_bl_s", "t_bl_e"):
            if float_key in entry and not isinstance(entry[float_key], (int, float)):
                raise ValueError(f"{phase}.{float_key} must be a number")
        if "points" in entry and not isinstance(entry["points"], dict):
            raise ValueError(f"{phase}.points must be a JSON object")
        if "cycles" in entry and not isinstance(entry["cycles"], list):
            raise ValueError(f"{phase}.cycles must be a JSON array")
    return data  # type: ignore[return-value]


# ── public API ────────────────────────────────────────────────────────────────

def load(dataset_path: Path) -> dict[str, dict]:
    """Return stored overrides for this dataset, or {} if none exist."""
    p = dataset_path / _FILENAME
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return _validate(raw)
    except json.JSONDecodeError as exc:
        log.warning("Overrides file is not valid JSON (%s): %s", p, exc)
    except ValueError as exc:
        log.warning("Overrides file failed schema check (%s): %s", p, exc)
    except Exception as exc:
        log.warning("Could not read overrides file (%s): %s", p, exc)
    return {}


def save(dataset_path: Path, overrides: dict[str, dict]) -> bool:
    """Persist overrides atomically.  Returns True on success, False on failure."""
    p   = dataset_path / _FILENAME
    tmp = p.with_suffix(".json.tmp")
    try:
        stamped = {
            phase: {**data, "saved_at": datetime.now().isoformat(timespec="seconds")}
            for phase, data in overrides.items()
        }
        tmp.write_text(json.dumps(stamped, indent=2), encoding="utf-8")
        os.replace(tmp, p)   # atomic on POSIX; near-atomic on Windows
        log.debug("Overrides saved: %s", p)
        return True
    except Exception as exc:
        log.warning("Could not save overrides (%s): %s", p, exc)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return False
