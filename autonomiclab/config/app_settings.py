"""Persistent application settings stored in ~/.autonomiclab/settings.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_SETTINGS_FILE = Path.home() / ".autonomiclab" / "settings.yaml"
_DEFAULT_DATA_FOLDER = Path.home() / "Projects" / "Python" / "Finapres" / "Files"


class AppSettings:
    """Load and persist user preferences.

    Settings are stored at ``~/.autonomiclab/settings.yaml``.
    Missing keys fall back to sensible defaults so a fresh install works
    without any configuration step.
    """

    def __init__(self) -> None:
        self._data: dict = {}
        self._load()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        if _SETTINGS_FILE.exists():
            try:
                with open(_SETTINGS_FILE, encoding="utf-8") as f:
                    self._data = yaml.safe_load(f) or {}
                log.debug("Settings loaded from %s", _SETTINGS_FILE)
            except Exception as exc:
                log.warning("Could not read settings file: %s", exc)
                self._data = {}

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
                yaml.dump(self._data, f, default_flow_style=False)
            log.debug("Settings saved to %s", _SETTINGS_FILE)
        except Exception as exc:
            log.warning("Could not save settings: %s", exc)

    # ── properties ───────────────────────────────────────────────────────────

    @property
    def data_folder(self) -> Path:
        """Default data folder."""
        return _DEFAULT_DATA_FOLDER

    @property
    def ui_zoom(self) -> int:
        return int(self._data.get("ui_zoom", 100))

    @ui_zoom.setter
    def ui_zoom(self, value: int) -> None:
        self._data["ui_zoom"] = max(50, min(200, value))
        self.save()
