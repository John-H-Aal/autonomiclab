"""Tests for DeepBreathingAnalyzer — FR-024 through FR-026.

Synthetic dataset
─────────────────
HR: sine wave, period = 10 s, amplitude ± 10 bpm around 70 bpm, active in [10, 70].
    → peaks at t = 12.5, 22.5, 32.5, 42.5, 52.5, 62.5  (HR = 80 bpm)
    → troughs at t = 17.5, 27.5, 37.5, 47.5, 57.5, 67.5 (HR = 60 bpm)
DBM2 marker at t = 10, DBM3 marker at t = 70.

Expected results:
  6 RSA cycles, each ΔHR = 20 bpm
  avg_rsa_all  = 20.0 bpm
  avg_rsa_top6 = 20.0 bpm  (all 6 cycles are in the top-6 set)
  n_sel        = 6
"""

import numpy as np
import pytest
from pathlib import Path

from autonomiclab.analysis.deep_breathing import DeepBreathingAnalyzer, DeepBreathingResult
from autonomiclab.core.models import Dataset, Marker, Signal


# ── helpers ───────────────────────────────────────────────────────────────────

def _sig(name, times, values, unit=""):
    return Signal(name, np.asarray(times, dtype=float),
                  np.asarray(values, dtype=float), unit)


def _make_db_dataset() -> tuple[Dataset, list[Marker]]:
    t = np.arange(0.0, 121.0, 0.5)   # 0.5 s resolution → 2 Hz
    v_hr = np.where(
        (t >= 10) & (t <= 70),
        70.0 + 10.0 * np.sin(2 * np.pi * (t - 10.0) / 10.0),
        70.0,
    )
    signals = {"HR": _sig("HR", t, v_hr, "bpm")}
    markers = [
        Marker(time=10.0, label="dbm2", phase="Deep Breathing"),
        Marker(time=70.0, label="dbm3", phase="Deep Breathing"),
    ]
    ds = Dataset(path=Path("/tmp/synth_db"), prefix="synth", signals=signals, markers=markers)
    return ds, markers


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db_dataset_and_markers():
    return _make_db_dataset()


@pytest.fixture(scope="module")
def db_result(db_dataset_and_markers):
    ds, markers = db_dataset_and_markers
    return DeepBreathingAnalyzer().analyze(ds, markers)


# ── FR-024: peak / trough detection ──────────────────────────────────────────

def test_correct_number_of_cycles(db_result):
    assert len(db_result.cycles) == 6


def test_all_cycles_have_positive_rsa(db_result):
    for c in db_result.cycles:
        assert c.rsa > 0, f"Cycle {c.cycle}: ΔHR must be positive"


def test_peaks_near_80_bpm(db_result):
    for c in db_result.cycles:
        assert c.max_v == pytest.approx(80.0, abs=0.5), (
            f"Cycle {c.cycle}: HR peak should be ~80 bpm, got {c.max_v:.1f}"
        )


def test_troughs_near_60_bpm(db_result):
    for c in db_result.cycles:
        assert c.min_v == pytest.approx(60.0, abs=0.5), (
            f"Cycle {c.cycle}: HR trough should be ~60 bpm, got {c.min_v:.1f}"
        )


# ── FR-025: peak–trough pairing ──────────────────────────────────────────────

def test_trough_always_after_peak(db_result):
    for c in db_result.cycles:
        assert c.min_t > c.max_t, (
            f"Cycle {c.cycle}: trough (t={c.min_t}) must follow peak (t={c.max_t})"
        )


def test_each_delta_hr_is_20(db_result):
    for c in db_result.cycles:
        assert c.rsa == pytest.approx(20.0, abs=0.5)


# ── FR-026: top-N selection and statistics ────────────────────────────────────

def test_avg_rsa_all(db_result):
    assert db_result.avg_rsa_all == pytest.approx(20.0, abs=0.5)


def test_avg_rsa_top6(db_result):
    assert db_result.avg_rsa_top6 == pytest.approx(20.0, abs=0.5)


def test_n_sel_is_6(db_result):
    assert db_result.n_sel == 6


def test_top6_set_contains_all_cycles(db_result):
    cycle_numbers = {c.cycle for c in db_result.cycles}
    assert db_result.top6 == cycle_numbers


def test_mean_max_all(db_result):
    assert db_result.mean_max_all == pytest.approx(80.0, abs=0.5)


def test_mean_min_all(db_result):
    assert db_result.mean_min_all == pytest.approx(60.0, abs=0.5)


# ── edge cases ────────────────────────────────────────────────────────────────

def test_missing_markers_returns_empty():
    """Without DBM2/DBM3 markers no analysis runs — cycles must be empty."""
    t = np.arange(0.0, 60.0, 0.5)
    v = 70.0 + 10.0 * np.sin(2 * np.pi * t / 10.0)
    ds = Dataset(
        path=Path("/tmp"), prefix="x",
        signals={"HR": _sig("HR", t, v, "bpm")},
        markers=[],
    )
    result = DeepBreathingAnalyzer().analyze(ds, [])
    assert result.cycles == []
    assert result.avg_rsa_all == 0.0


def test_missing_hr_signal_returns_empty():
    ds = Dataset(path=Path("/tmp"), prefix="x", signals={}, markers=[
        Marker(time=10.0, label="dbm2", phase="Deep Breathing"),
        Marker(time=70.0, label="dbm3", phase="Deep Breathing"),
    ])
    result = DeepBreathingAnalyzer().analyze(ds, ds.markers)
    assert result.cycles == []


# ── apply_cycle_overrides ─────────────────────────────────────────────────────

def test_apply_cycle_overrides_replaces_cycles(db_dataset_and_markers):
    """Manually supplied cycles must replace auto-detected ones and recompute stats."""
    ds, _ = db_dataset_and_markers
    # Provide only 2 manual cycles using the known peak/trough times
    stored = [
        {"cycle": 1, "max_t": 12.5, "min_t": 17.5},
        {"cycle": 2, "max_t": 22.5, "min_t": 27.5},
    ]
    result = DeepBreathingResult()
    DeepBreathingAnalyzer().apply_cycle_overrides(result, ds, stored)

    assert len(result.cycles) == 2
    assert result.avg_rsa_all == pytest.approx(20.0, abs=0.5)
    assert result.n_sel == 2


def test_apply_empty_cycle_overrides(db_dataset_and_markers):
    """An empty cycle list must zero out all statistics."""
    ds, _ = db_dataset_and_markers
    result = DeepBreathingResult()
    DeepBreathingAnalyzer().apply_cycle_overrides(result, ds, [])

    assert result.cycles == []
    assert result.avg_rsa_all == 0.0
    assert result.avg_rsa_top6 == 0.0
