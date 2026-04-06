"""Application settings.

Two-layer configuration:
  1. config.yaml  — admin-managed, lives next to the .exe (or project root in dev)
  2. ~/.autonomiclab/settings.yaml — per-user preferences (zoom, last folder)
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_USER_SETTINGS_FILE = Path.home() / ".autonomiclab" / "settings.yaml"
_DEFAULT_DATA_FOLDER = Path.home() / "Documents" / "data"


def _app_dir() -> Path:
    """Return the directory containing the executable (or project root in dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


class AppSettings:
    """Merged view of admin config and per-user preferences."""

    def __init__(self) -> None:
        self._config: dict = {}   # config.yaml  (admin)
        self._prefs: dict = {}    # settings.yaml (user)
        self._load_config()
        self._load_prefs()

    # ── loaders ──────────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        config_file = _app_dir() / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                log.debug("Config loaded from %s", config_file)
            except Exception as exc:
                log.warning("Could not read config.yaml: %s", exc)

    def _load_prefs(self) -> None:
        if _USER_SETTINGS_FILE.exists():
            try:
                with open(_USER_SETTINGS_FILE, encoding="utf-8") as f:
                    self._prefs = yaml.safe_load(f) or {}
                log.debug("Preferences loaded from %s", _USER_SETTINGS_FILE)
            except Exception as exc:
                log.warning("Could not read settings file: %s", exc)

    def save(self) -> None:
        """Persist user preferences to disk."""
        try:
            _USER_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_USER_SETTINGS_FILE, "w", encoding="utf-8") as f:
                yaml.dump(self._prefs, f, default_flow_style=False)
        except Exception as exc:
            log.warning("Could not save settings: %s", exc)

    # ── properties ───────────────────────────────────────────────────────────

    @property
    def data_folder(self) -> Path:
        """Last used folder (user pref) → config.yaml default → fallback."""
        if saved := self._prefs.get("data_folder"):
            return Path(saved)
        if configured := self._config.get("data_folder"):
            return Path(configured)
        return _DEFAULT_DATA_FOLDER

    @data_folder.setter
    def data_folder(self, value: Path) -> None:
        self._prefs["data_folder"] = str(value)
        self.save()

    @property
    def allowed_users(self) -> list[str]:
        """List of allowed usernames, or empty list to allow everyone."""
        return self._config.get("allowed_users") or []

    @property
    def ui_zoom(self) -> int:
        return int(self._prefs.get("ui_zoom", 100))

    @ui_zoom.setter
    def ui_zoom(self, value: int) -> None:
        self._prefs["ui_zoom"] = max(50, min(200, value))
        self.save()
