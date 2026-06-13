"""Tests for ValsalvaAnalyzer — FR-017 through FR-023.

Synthetic dataset ground truth
───────────────────────────────
PAirway  : 0 mmHg outside [50, 65), 25 mmHg inside — clean threshold crossings.
reSYS    : piecewise linear waveform at 0.5 s resolution.
HR       : piecewise linear trend at 1 s resolution.
vm1 marker at t = 49 s.

Expected values (all computed analytically):
  t_S1s    ≈ 49.51 s    (PAirway 0→25 crossing, interpolated)
  t_bl_s   ≈  4.51 s    (t_S1s − 45)
  t_bl_e   ≈ 34.51 s    (t_S1s − 15)
  avg_sbp  = 120.0 mmHg
  t_S1e    =  52.0 s    (first local SBP max = 126 mmHg)
  t_S2es   =  56.0 s    v_nadir  =  80.0 mmHg
  t_S2lmax =  63.0 s    v_S2lmax = 100.0 mmHg
  t_S3s    ≈ 64.99 s    (PAirway 25→0 crossing, interpolated)
  t_S3e    =  67.0 s    v_S3min  =  70.0 mmHg
  hr_max_t =  66.0 s    hr_max_v = 105.0 bpm
  hr_min_t =  86.0 s    hr_min_v =  55.0 bpm
  t_S4e    =  96.0 s    (hr_max_t + 30)
  t_ov     =  78.0 s    v_ov     = 145.0 mmHg
  PRT      =   6.0 s    (SBP returns to 120 at t = 73)
  A        =  40.0 mmHg (avg_sbp − v_nadir)
  B        =  20.0 mmHg (v_S2lmax − v_nadir)
  VR       ≈   1.909    (105 / 55)
  BRSa     ≈   9.17 mmHg/s  ((A + 0.75 B) / PRT = 55 / 6)
"""

import numpy as np
import pytest
from pathlib import Path

from autonomiclab.analysis.valsalva import ValsalvaAnalyzer, ValsalvaResult
from autonomiclab.core.models import Dataset, Marker, Signal


# ── helpers ───────────────────────────────────────────────────────────────────

def _sig(name: str, times, values, unit: str = "") -> Signal:
    return Signal(name, np.asarray(times, dtype=float),
                  np.asarray(values, dtype=float), unit)


def _make_reSYS(t: np.ndarray) -> np.ndarray:
    """Piecewise SBP (mmHg).

    Segment:          range      start → end
    baseline          [0, 50)    120
    Phase I rise      [50, 52)   120 → 126
    IIe fall          [52, 56)   126 →  80
    IIl rise          [56, 63)    80 → 100
    pre-release       [63, 65)   100 →  90
    Phase III fall    [65, 67)    90 →  70
    return to BL      [67, 73)    70 → 120
    overshoot rise    [73, 78)   120 → 145
    overshoot fall    [78, 83)   145 → 120
    stable            [83, …)    120
    """
    def lin(t_, t0, v0, t1, v1):
        return v0 + (t_ - t0) * (v1 - v0) / (t1 - t0)

    return np.select(
        [
            t < 50,
            (t >= 50) & (t < 52),
            (t >= 52) & (t < 56),
            (t >= 56) & (t < 63),
            (t >= 63) & (t < 65),
            (t >= 65) & (t < 67),
            (t >= 67) & (t < 73),
            (t >= 73) & (t < 78),
            (t >= 78) & (t < 83),
        ],
        [
            120,
            lin(t, 50, 120, 52, 126),
            lin(t, 52, 126, 56, 80),
            lin(t, 56, 80,  63, 100),
            lin(t, 63, 100, 65, 90),
            lin(t, 65, 90,  67, 70),
            lin(t, 67, 70,  73, 120),
            lin(t, 73, 120, 78, 145),
            lin(t, 78, 145, 83, 120),
        ],
        default=120.0,
    )


def _make_HR(t: np.ndarray) -> np.ndarray:
    """Piecewise HR (bpm) at 1 s resolution."""
    def lin(t_, t0, v0, t1, v1):
        return v0 + (t_ - t0) * (v1 - v0) / (t1 - t0)

    return np.select(
        [
            t < 50,
            (t >= 50) & (t < 66),
            (t >= 66) & (t < 86),
        ],
        [
            70.0,
            lin(t, 50, 70, 66, 105),
            lin(t, 66, 105, 86, 55),
        ],
        default=lin(t, 86, 55, 120, 70),
    )


def _make_valsalva_dataset(include_post_release_cal: bool = False) -> tuple[Dataset, list[Marker]]:
    t_hi = np.arange(0.0, 121.0, 0.5)   # 0.5 s grid for PAirway + reSYS
    t_hr = np.arange(0.0, 121.0, 1.0)   # 1 s grid for HR

    v_pa  = np.where((t_hi >= 50) & (t_hi < 65), 25.0, 0.0)
    v_sys = _make_reSYS(t_hi)
    v_hr  = _make_HR(t_hr)

    signals = {
        "PAirway": _sig("PAirway", t_hi, v_pa,  "mmHg"),
        "reSYS":   _sig("reSYS",   t_hi, v_sys, "mmHg"),
        "HR":      _sig("HR",      t_hr, v_hr,  "bpm"),
    }

    if include_post_release_cal:
        # PhysioCalActive = 1 in [75, 90) — inside post-release window [t_S3s, t_S4e]
        v_cal = np.where((t_hi >= 75) & (t_hi < 90), 1.0, 0.0)
        signals["PhysioCalActive"] = _sig("PhysioCalActive", t_hi, v_cal)

    markers = [Marker(time=49.0, label="vm1", phase="Valsalva")]
    ds = Dataset(path=Path("/tmp/synth_val"), prefix="synth",
                 signals=signals, markers=markers)
    return ds, markers


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def result():
    ds, markers = _make_valsalva_dataset()
    return ValsalvaAnalyzer().analyze(ds, markers)


@pytest.fixture(scope="module")
def cal_result():
    ds, markers = _make_valsalva_dataset(include_post_release_cal=True)
    return ValsalvaAnalyzer().analyze(ds, markers)


# ── FR-018: Phase I start (PAirway upward crossing) ───────────────────────────

def test_t_S1s_detected(result):
    assert result.t_S1s is not None


def test_t_S1s_near_expected(result):
    # PAirway crosses 0.5 upward between t=49.5 (v=0) and t=50.0 (v=25)
    # Interpolated: 49.5 + (0.5/25) * 0.5 = 49.51
    assert result.t_S1s == pytest.approx(49.51, abs=0.05)


# ── FR-019: Phase III start (PAirway downward crossing) ───────────────────────

def test_t_S3s_detected(result):
    assert result.t_S3s is not None


def test_t_S3s_near_expected(result):
    # PAirway crosses 0.5 downward between t=64.5 (v=25) and t=65.0 (v=0)
    # Interpolated: 64.5 + (24.5/25) * 0.5 = 64.99
    assert result.t_S3s == pytest.approx(64.99, abs=0.05)


# ── FR-020: baseline window placement ────────────────────────────────────────

def test_baseline_window_45_to_15_before_S1s(result):
    assert result.t_bl_s == pytest.approx(result.t_S1s - 45.0, abs=0.01)
    assert result.t_bl_e == pytest.approx(result.t_S1s - 15.0, abs=0.01)


def test_avg_sbp_equals_120(result):
    # Baseline is flat at 120 mmHg → mean must equal 120.0 exactly
    assert result.avg_sbp == pytest.approx(120.0, abs=0.1)


# ── FR-017: all phase boundaries present ────────────────────────────────────

def test_all_phase_boundaries_not_none(result):
    for attr in ("t_bl_s", "t_bl_e", "t_S1s", "t_S1e",
                 "t_S2es", "t_S2lmax", "t_S3s", "t_S3e", "t_S4e"):
        assert getattr(result, attr) is not None, f"{attr} must not be None"


def test_t_S1e_is_phase_I_peak(result):
    assert result.t_S1e == pytest.approx(52.0, abs=0.5)


def test_nadir_time_and_value(result):
    assert result.t_S2es == pytest.approx(56.0, abs=0.5)
    assert result.v_nadir == pytest.approx(80.0, abs=0.5)


def test_S2lmax_time_and_value(result):
    assert result.t_S2lmax == pytest.approx(63.0, abs=0.5)
    assert result.v_S2lmax == pytest.approx(100.0, abs=0.5)


def test_phase_III_nadir(result):
    assert result.t_S3e == pytest.approx(67.0, abs=0.5)
    assert result.v_S3min == pytest.approx(70.0, abs=0.5)


def test_overshoot(result):
    assert result.t_ov == pytest.approx(78.0, abs=0.5)
    assert result.v_ov == pytest.approx(145.0, abs=1.0)


# ── FR-021: HR max search window ────────────────────────────────────────────

def test_hr_max_detected(result):
    assert result.hr_max_t is not None
    assert result.hr_max_v is not None


def test_hr_max_within_search_window(result):
    assert result.t_S2es <= result.hr_max_t <= (result.t_S3s + 5.0)


def test_hr_max_value(result):
    assert result.hr_max_v == pytest.approx(105.0, abs=0.5)


# ── FR-022: HR min search window ────────────────────────────────────────────

def test_hr_min_detected(result):
    assert result.hr_min_t is not None
    assert result.hr_min_v is not None


def test_hr_min_within_search_window(result):
    assert result.hr_max_t <= result.hr_min_t <= (result.hr_max_t + 30.0)


def test_hr_min_value(result):
    assert result.hr_min_v == pytest.approx(55.0, abs=0.5)


# ── FR-017: derived parameters ───────────────────────────────────────────────

def test_A_equals_40(result):
    assert result.A == pytest.approx(40.0, abs=0.5)


def test_B_equals_20(result):
    assert result.B == pytest.approx(20.0, abs=0.5)


def test_PRT_equals_6(result):
    assert result.PRT is not None
    assert result.PRT == pytest.approx(6.0, abs=0.5)


def test_VR_ratio(result):
    assert result.VR == pytest.approx(105.0 / 55.0, abs=0.05)


def test_BRSa_formula(result):
    r = result
    assert r.BRSa is not None
    if r.A is not None and r.B is not None and r.PRT:
        assert r.BRSa == pytest.approx((r.A + 0.75 * r.B) / r.PRT, rel=0.01)


def test_S4e_equals_hr_max_plus_30(result):
    assert result.t_S4e == pytest.approx(result.hr_max_t + 30.0, abs=0.1)


# ── FR-023: PhysioCalActive contamination ────────────────────────────────────

def test_no_cal_warnings_on_clean_signal(result):
    assert result.cal_warnings == []


def test_cal_warning_fired(cal_result):
    assert "Phase III+IV" in cal_result.cal_warnings


def test_cal_suppresses_phase_iv_times(cal_result):
    assert cal_result.t_S4e is None
    assert cal_result.hr_min_t is None
    assert cal_result.hr_min_v is None


def test_cal_suppresses_prt(cal_result):
    assert cal_result.PRT is None


def test_cal_suppresses_phase_iii_end(cal_result):
    assert cal_result.t_S3e is None
    assert cal_result.v_S3min is None


# ── missing signals → empty result ───────────────────────────────────────────

def test_missing_signals_returns_empty_result():
    ds = Dataset(path=Path("/tmp"), prefix="x", signals={
        "PAirway": _sig("PAirway", [0.0, 1.0], [0.0, 0.0]),
        "reSYS":   _sig("reSYS",   [0.0, 1.0], [120.0, 120.0]),
        # HR deliberately absent
    })
    r = ValsalvaAnalyzer().analyze(ds, [])
    assert r.t_S1s is None
    assert r.VR is None
    assert r.BRSa is None


# ── OQ-005 fix: t_anchor uses t_start when no vm1 marker in window ───────────

def test_t_anchor_uses_t_start_not_recording_start():
    """Without a vm1 marker, t_start must be used as the anchor so that the
    phase detector does not find PAirway crossings from an earlier manoeuvre."""
    t = np.arange(0.0, 121.0, 0.5)

    # False crossing at t = 5–8 (earlier manoeuvre — must be ignored)
    # Real crossing at t = 50–65
    v_pa = np.where(
        ((t >= 5) & (t < 8)) | ((t >= 50) & (t < 65)),
        25.0,
        0.0,
    )
    v_sys = np.full_like(t, 120.0)
    t_hr  = np.arange(0.0, 121.0, 1.0)
    v_hr  = np.full_like(t_hr, 70.0)

    signals = {
        "PAirway": _sig("PAirway", t, v_pa,  "mmHg"),
        "reSYS":   _sig("reSYS",   t, v_sys, "mmHg"),
        "HR":      _sig("HR",      t_hr, v_hr, "bpm"),
    }
    ds = Dataset(path=Path("/tmp"), prefix="x", signals=signals, markers=[])

    # No vm1 marker; pass t_start=49 → anchor must be 49, not t_pa[0]=0
    r = ValsalvaAnalyzer().analyze(ds, [], t_start=49.0, t_end=80.0)

    assert r.t_S1s is not None
    assert r.t_S1s > 49.0, (
        f"t_S1s={r.t_S1s:.2f} should be after t_start=49 — "
        "the false crossing at t=5 must be ignored"
    )
