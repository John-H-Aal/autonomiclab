"""Integration tests for DatasetService (CSV and NSC load paths)."""

from pathlib import Path
import pytest

from autonomiclab.core.dataset_service import DatasetService


@pytest.fixture(scope="module")
def svc():
    return DatasetService()


# ── CSV path ──────────────────────────────────────────────────────────────────

def test_csv_load_returns_dataset(svc, csv_folder):
    ds = svc.load(csv_folder)
    assert ds is not None
    assert ds.prefix == "2026-02-02_10.33.58"


def test_csv_load_has_signals(svc, csv_folder):
    ds = svc.load(csv_folder)
    assert len(ds.signals) > 0
    assert ds.has_signal("HR") or ds.has_signal("reBAP")


def test_csv_load_has_markers(svc, csv_folder):
    ds = svc.load(csv_folder)
    assert len(ds.markers) > 0


def test_csv_load_path_is_folder(svc, csv_folder):
    ds = svc.load(csv_folder)
    assert ds.path == csv_folder


def test_csv_missing_folder_raises(svc):
    with pytest.raises(FileNotFoundError):
        svc.load(Path("/nonexistent/folder"))


# ── NSC path ──────────────────────────────────────────────────────────────────

def test_nsc_load_returns_dataset(svc, nsc_file):
    ds = svc.load_nsc(nsc_file)
    assert ds is not None
    assert len(ds.signals) > 0


def test_nsc_load_has_no_markers(svc, nsc_file):
    """NSC format carries no protocol event annotations."""
    ds = svc.load_nsc(nsc_file)
    assert ds.markers == []
    assert ds.region_markers == {}


def test_nsc_load_prefix_is_stem(svc, nsc_file):
    ds = svc.load_nsc(nsc_file)
    assert ds.prefix == nsc_file.stem


def test_nsc_missing_file_raises(svc):
    with pytest.raises(FileNotFoundError):
        svc.load_nsc(Path("/nonexistent/file.nsc"))


# ── Dataset model ─────────────────────────────────────────────────────────────

def test_phase_window_falls_back_to_hr_range(svc, csv_folder):
    ds = svc.load(csv_folder)
    t0, t1 = ds.phase_window("Nonexistent Phase")
    assert t1 > t0


def test_get_signal_returns_none_for_missing(svc, csv_folder):
    ds = svc.load(csv_folder)
    assert ds.get_signal("DOESNOTEXIST") is None
