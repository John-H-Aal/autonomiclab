"""Tests for per-dataset override persistence — FR-033 and NFR-004."""

import json
import pytest
from pathlib import Path

from autonomiclab.core.overrides import load, save


# ── FR-033: save / load round-trip ───────────────────────────────────────────

def test_save_returns_true_on_success(tmp_path):
    assert save(tmp_path, {"Valsalva test 1": {"t_bl_s": 5.0}}) is True


def test_load_missing_returns_empty_dict(tmp_path):
    assert load(tmp_path) == {}


def test_round_trip_preserves_values(tmp_path):
    data = {
        "Valsalva test 1": {
            "t_bl_s": 5.0,
            "t_bl_e": 35.0,
            "points": {"t_S1e": 52.0, "t_S2es": 56.0},
        }
    }
    save(tmp_path, data)
    loaded = load(tmp_path)

    assert loaded["Valsalva test 1"]["t_bl_s"] == pytest.approx(5.0)
    assert loaded["Valsalva test 1"]["t_bl_e"] == pytest.approx(35.0)
    assert loaded["Valsalva test 1"]["points"]["t_S1e"] == pytest.approx(52.0)


def test_save_adds_saved_at_timestamp(tmp_path):
    save(tmp_path, {"phase": {"t_bl_s": 1.0}})
    loaded = load(tmp_path)
    assert "saved_at" in loaded["phase"]


def test_multiple_phases_preserved(tmp_path):
    data = {
        "Valsalva test 1":   {"t_bl_s": 5.0},
        "Deep Breathing 1":  {"cycles": [{"cycle": 1, "max_t": 12.5, "min_t": 17.5}]},
    }
    save(tmp_path, data)
    loaded = load(tmp_path)

    assert "Valsalva test 1" in loaded
    assert "Deep Breathing 1" in loaded
    assert loaded["Deep Breathing 1"]["cycles"][0]["max_t"] == pytest.approx(12.5)


# ── schema validation on load ─────────────────────────────────────────────────

def test_load_invalid_json_returns_empty(tmp_path):
    (tmp_path / "overrides.json").write_text("not valid json {{{", encoding="utf-8")
    assert load(tmp_path) == {}


def test_load_wrong_top_level_type_returns_empty(tmp_path):
    (tmp_path / "overrides.json").write_text('["list", "not", "dict"]', encoding="utf-8")
    assert load(tmp_path) == {}


def test_load_phase_entry_not_dict_returns_empty(tmp_path):
    (tmp_path / "overrides.json").write_text('{"phase": "string_not_dict"}', encoding="utf-8")
    assert load(tmp_path) == {}


def test_load_invalid_float_field_returns_empty(tmp_path):
    (tmp_path / "overrides.json").write_text(
        '{"phase": {"t_bl_s": "not_a_number"}}', encoding="utf-8"
    )
    assert load(tmp_path) == {}


# ── NFR-004: atomic write — no leftover .tmp file ────────────────────────────

def test_no_tmp_file_after_successful_save(tmp_path):
    save(tmp_path, {"phase": {"t_bl_s": 1.0}})
    assert not (tmp_path / "overrides.json.tmp").exists()


def test_second_save_overwrites_first(tmp_path):
    save(tmp_path, {"phase": {"t_bl_s": 1.0}})
    save(tmp_path, {"phase": {"t_bl_s": 99.0}})
    assert load(tmp_path)["phase"]["t_bl_s"] == pytest.approx(99.0)


def test_save_fails_gracefully_on_read_only_path(tmp_path):
    """save() must return False (not raise) when the directory is not writable."""
    import os, stat
    ro = tmp_path / "readonly"
    ro.mkdir()
    ro.chmod(stat.S_IRUSR | stat.S_IXUSR)  # read + execute only
    try:
        result = save(ro, {"phase": {}})
        assert result is False
    finally:
        ro.chmod(stat.S_IRWXU)  # restore so tmp_path cleanup works
