"""Tests for AppSettings.data_folder — FR-062.

Tests the tilde expansion and auto-mkdir behaviour without loading real
config files by constructing AppSettings via __new__ and injecting
_config / _prefs directly.
"""

import pytest
from pathlib import Path

from autonomiclab.config.app_settings import AppSettings


def _settings(config: dict = None, prefs: dict = None) -> AppSettings:
    """Build an AppSettings instance without reading any files."""
    s = AppSettings.__new__(AppSettings)
    s._config = config or {}
    s._prefs  = prefs  or {}
    return s


# ── FR-062: tilde expansion ───────────────────────────────────────────────────

def test_config_tilde_is_expanded(tmp_path, monkeypatch):
    """~ in config.yaml data_folder must be expanded to an absolute path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    s = _settings(config={"data_folder": "~/al_test_data"})
    folder = s.data_folder
    assert "~" not in str(folder)
    assert folder.is_absolute()
    assert folder.name == "al_test_data"


def test_prefs_tilde_is_expanded(tmp_path, monkeypatch):
    """~ in user preferences data_folder must also be expanded."""
    monkeypatch.setenv("HOME", str(tmp_path))
    existing = tmp_path / "al_prefs_data"
    existing.mkdir()
    s = _settings(prefs={"data_folder": str(existing).replace(str(tmp_path), "~")})
    folder = s.data_folder
    assert "~" not in str(folder)
    assert folder.is_absolute()


def test_default_path_has_no_tilde():
    """The default ~/Documents/AutonomicLab/data must not contain a literal ~."""
    s = _settings()
    assert "~" not in str(s.data_folder)
    assert s.data_folder.is_absolute()


# ── FR-062: auto-mkdir ────────────────────────────────────────────────────────

def test_configured_folder_created_when_absent(tmp_path, monkeypatch):
    """data_folder from config.yaml must be created if it does not yet exist."""
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "new_data_dir"
    assert not target.exists()
    s = _settings(config={"data_folder": str(target)})
    folder = s.data_folder
    assert folder.exists()
    assert folder.is_dir()


def test_default_folder_created_when_absent(tmp_path, monkeypatch):
    """The default ~/Documents/AutonomicLab/data must be created on first access."""
    monkeypatch.setenv("HOME", str(tmp_path))
    s = _settings()
    folder = s.data_folder
    assert folder.exists()
    assert folder.is_dir()


# ── priority order ────────────────────────────────────────────────────────────

def test_prefs_override_config_when_exists(tmp_path):
    """User preferences override config.yaml when the pref path exists."""
    pref_dir    = tmp_path / "pref_data"
    config_dir  = tmp_path / "config_data"
    pref_dir.mkdir()
    config_dir.mkdir()
    s = _settings(
        config={"data_folder": str(config_dir)},
        prefs= {"data_folder": str(pref_dir)},
    )
    assert s.data_folder == pref_dir


def test_config_used_when_prefs_path_missing(tmp_path):
    """If the prefs path does not exist, fall through to config.yaml."""
    config_dir = tmp_path / "config_data"
    config_dir.mkdir()
    s = _settings(
        config={"data_folder": str(config_dir)},
        prefs= {"data_folder": str(tmp_path / "nonexistent")},
    )
    assert s.data_folder == config_dir
