"""Tests for marker phase classification and region marker CSV loading.

Covers FR-012 (load_region_markers) and FR-013 (determine_phase).
"""

import pytest
from pathlib import Path

from autonomiclab.core.markers_handler import determine_phase, load_region_markers


# ── FR-013: phase classification ──────────────────────────────────────────────

@pytest.mark.parametrize("label,expected", [
    # Valsalva keywords
    ("vm1",           "Valsalva"),
    ("VM2",           "Valsalva"),
    ("Valsalva 1",    "Valsalva"),
    ("START VM",      "Valsalva"),
    # Stand Test keywords
    ("sm1",           "Stand Test"),
    ("SM2",           "Stand Test"),
    ("stand up",      "Stand Test"),
    ("Stand test",    "Stand Test"),
    # Deep Breathing keywords
    ("dbm2",          "Deep Breathing"),
    ("DBM3",          "Deep Breathing"),
    ("deep breath 1", "Deep Breathing"),
    ("breath",        "Deep Breathing"),
    # Other
    ("annotation",    "Other"),
    ("noise",         "Other"),
    ("",              "Other"),
    ("12345",         "Other"),
])
def test_determine_phase(label, expected):
    assert determine_phase(label) == expected


# ── FR-012: region marker CSV loading ─────────────────────────────────────────

def _write_region_csv(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_region_markers_single_region(tmp_path):
    _write_region_csv(
        tmp_path / "2026-01-01_12.00.00_RegionMarkers.csv",
        "Time;Label\n"
        "10.0;Start Valsalva\n"
        "45.0;End Valsalva\n",
    )
    result = load_region_markers(tmp_path, "2026-01-01_12.00.00")
    assert "Valsalva" in result
    t0, t1 = result["Valsalva"]
    assert t0 == pytest.approx(10.0)
    assert t1 == pytest.approx(45.0)


def test_load_region_markers_multiple_regions(tmp_path):
    _write_region_csv(
        tmp_path / "2026-01-01_12.00.00_RegionMarkers.csv",
        "Time;Label\n"
        "10.0;Start Valsalva\n"
        "45.0;End Valsalva\n"
        "60.0;Start Deep Breathing\n"
        "120.0;End Deep Breathing\n",
    )
    result = load_region_markers(tmp_path, "2026-01-01_12.00.00")
    assert len(result) == 2
    assert result["Valsalva"]        == pytest.approx((10.0, 45.0))
    assert result["Deep Breathing"]  == pytest.approx((60.0, 120.0))


def test_load_region_markers_missing_file_returns_empty(tmp_path):
    result = load_region_markers(tmp_path, "nonexistent_prefix")
    assert result == {}


def test_load_region_markers_unpaired_start_dropped(tmp_path):
    """A 'Start X' with no 'End X' shall be silently dropped."""
    _write_region_csv(
        tmp_path / "2026-01-01_12.00.00_RegionMarkers.csv",
        "Time;Label\n"
        "10.0;Start Valsalva\n",
    )
    result = load_region_markers(tmp_path, "2026-01-01_12.00.00")
    assert "Valsalva" not in result


def test_load_region_markers_skips_header(tmp_path):
    """A header row starting with 'time' must be ignored."""
    _write_region_csv(
        tmp_path / "2026-01-01_12.00.00_RegionMarkers.csv",
        "Time;Label\n"
        "10.0;Start Valsalva\n"
        "45.0;End Valsalva\n",
    )
    result = load_region_markers(tmp_path, "2026-01-01_12.00.00")
    assert len(result) == 1


def test_load_region_markers_space_variant_filename(tmp_path):
    """Space-separated variant '{PREFIX} RegionMarkers.csv' is also accepted."""
    _write_region_csv(
        tmp_path / "2026-01-01_12.00.00 RegionMarkers.csv",
        "10.0;Start Stand Test\n"
        "50.0;End Stand Test\n",
    )
    result = load_region_markers(tmp_path, "2026-01-01_12.00.00")
    assert "Stand Test" in result
