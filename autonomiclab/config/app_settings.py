"""Application settings.

Two-layer configuration:
  1. config.yaml  — admin-managed, lives next to the .exe (or project root in dev)
  2. ~/.autonomiclab/settings.yaml — per-user preferences (zoom, last folder)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)

_USER_SETTINGS_FILE = Path.home() / ".autonomiclab" / "settings.yaml"
_DEFAULT_DATA_FOLDER = Path.home() / "Documents" / "AutonomicLab" / "data"


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
        """Data folder: user prefs override config.yaml, fallback ~/Documents/AutonomicLab/data."""
        if override := self._prefs.get("data_folder"):
            p = Path(override)
            if p.exists():
                return p
        if configured := self._config.get("data_folder"):
            return Path(configured)
        return _DEFAULT_DATA_FOLDER

    @property
    def allowed_users(self) -> list[str]:
        """List of allowed usernames, or empty list to allow everyone."""
        return self._config.get("allowed_users") or []

    @property
    def users_db_token(self) -> str:
        """GitHub Personal Access Token for users.db sync. Empty = no sync."""
        return self._config.get("users_db_token") or ""

    @property
    def users_db_admin_token(self) -> str:
        """GitHub Personal Access Token for admin push. Empty = no push."""
        return self._config.get("users_db_admin_token") or ""

    def set_admin_token(self, token: str) -> bool:
        """Persist users_db_admin_token to config.yaml. Returns True on success."""
        config_file = _app_dir() / "config.yaml"
        try:
            text = config_file.read_text(encoding="utf-8") if config_file.exists() else ""
            line = f'users_db_admin_token: "{token}"'
            if re.search(r"^users_db_admin_token:", text, re.MULTILINE):
                text = re.sub(r"^users_db_admin_token:.*$", line, text, flags=re.MULTILINE)
            elif re.search(r"^users_db_token:", text, re.MULTILINE):
                text = re.sub(r"(^users_db_token:.*$)", r"\1\n" + line, text, flags=re.MULTILINE)
            else:
                text = text.rstrip("\n") + f"\n{line}\n"
            config_file.write_text(text, encoding="utf-8")
            self._config["users_db_admin_token"] = token
            log.info("Admin token saved to %s", config_file)
            return True
        except Exception as exc:
            log.warning("Could not save admin token: %s", exc)
            return False

    @property
    def allow_guest(self) -> bool:
        """Whether the guest login button is shown. Default True."""
        return bool(self._config.get("allow_guest", True))

    @property
    def users_db_path(self) -> Path:
        """Local path for the encrypted users database."""
        return _app_dir() / "users.db"

    @property
    def ui_zoom(self) -> int:
        return int(self._prefs.get("ui_zoom", 100))

    @ui_zoom.setter
    def ui_zoom(self, value: int) -> None:
        self._prefs["ui_zoom"] = max(50, min(200, value))
        self.save()
