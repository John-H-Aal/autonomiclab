"""Tests for the Finapres NOVA .nsc binary reader.

Ground truth values are from exam 12091FR (2026-04-20), validated empirically
during format reverse-engineering:
  fiSYS ≈ 125.6 mmHg,  fiDIA ≈ 79.0 mmHg,  HR ≈ 71.2 bpm
  reBAP median ≈ 94 mmHg,  IBI ≈ 837 ms
"""

from pathlib import Path
import numpy as np
import pytest

from autonomiclab.core.nsc_reader import NscReader


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def reader(nsc_file):
    with NscReader(nsc_file) as r:
        yield r


# ── structural ────────────────────────────────────────────────────────────────

def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        NscReader("/nonexistent/file.nsc")


def test_unknown_channel_raises(reader):
    with pytest.raises(KeyError):
        reader.read("NOT_A_CHANNEL")


def test_channels_not_empty(reader):
    assert len(reader.channels()) > 0


def test_expected_channels_present(reader):
    channels = set(reader.channels())
    for name in ("fiAP", "reBAP", "HR"):
        assert name in channels, f"Expected channel '{name}' not found"


def test_context_manager_closes_zip(nsc_file):
    with NscReader(nsc_file) as r:
        assert len(r.channels()) > 0
    # zipfile sets fp=None on close; opening a member must then raise
    with pytest.raises(Exception):
        r._zf.open(r._zf.namelist()[0])


# ── signal shape and time axis ────────────────────────────────────────────────

def test_times_values_same_length(reader):
    for ch in ("reBAP", "HR", "fiAP"):
        sig = reader.read(ch)
        assert len(sig.times) == len(sig.values), f"{ch}: array length mismatch"


def test_times_monotonically_non_decreasing(reader):
    sig = reader.read("reBAP")
    assert np.all(np.diff(sig.times) >= 0), "reBAP timestamps not monotonically increasing"


def test_times_in_seconds(reader):
    """reBAP at 200 Hz should have sample spacing ~5 ms, not 50 µs or 5 s."""
    sig = reader.read("reBAP")
    median_dt = float(np.median(np.diff(sig.times[~np.isnan(sig.times)])))
    assert 0.001 < median_dt < 0.1, f"Unexpected sample interval {median_dt:.6f} s"


# ── physical values ───────────────────────────────────────────────────────────

def test_hr_physiological_range(reader):
    sig = reader.read("HR")
    valid = sig.values[~np.isnan(sig.values)]
    median_hr = float(np.median(valid))
    assert 40 < median_hr < 120, f"HR median {median_hr:.1f} outside physiological range"


def test_hr_close_to_ground_truth(reader):
    sig = reader.read("HR")
    valid = sig.values[~np.isnan(sig.values)]
    assert float(np.median(valid)) == pytest.approx(71.2, abs=5.0)


def test_rebap_physiological_range(reader):
    sig = reader.read("reBAP")
    valid = sig.values[~np.isnan(sig.values)]
    median_bp = float(np.median(valid))
    assert 50 < median_bp < 200, f"reBAP median {median_bp:.1f} mmHg outside range"


def test_fiap_sys_dia_ground_truth(reader):
    """Beat-by-beat fiSYS and fiDIA must match validated ground truth within 5 mmHg."""
    for name, expected in (("fiSYS", 125.6), ("fiDIA", 79.0)):
        if name not in reader.channels():
            pytest.skip(f"{name} not in this file")
        sig = reader.read(name)
        valid = sig.values[~np.isnan(sig.values)]
        assert float(np.median(valid)) == pytest.approx(expected, abs=5.0), (
            f"{name} median {float(np.median(valid)):.1f} vs expected {expected}"
        )


# ── gap / Physiocal ───────────────────────────────────────────────────────────

def test_gap_mask_matches_nan_values(reader):
    """Every gap-masked sample must be NaN in the signal, and vice versa."""
    sig = reader.read("fiAP")
    mask = reader.gap_mask("fiAP")
    np.testing.assert_array_equal(np.isnan(sig.values), mask)


def test_gap_mask_length_matches_signal(reader):
    sig = reader.read("reBAP")
    mask = reader.gap_mask("reBAP")
    assert len(mask) == len(sig.times)


# ── metadata accessors ────────────────────────────────────────────────────────

def test_sample_rate_reasonable(reader):
    assert 100 <= reader.sample_rate("reBAP") <= 500   # waveform: expect ~200 Hz
    assert reader.sample_rate("HR") < 10               # trend: expect ~1 Hz


def test_units_non_empty(reader):
    assert reader.units("reBAP") != ""
    assert reader.units("HR") != ""


def test_signal_type(reader):
    assert reader.signal_type("reBAP") == "Waveform"
    assert reader.signal_type("HR") == "Trend"
