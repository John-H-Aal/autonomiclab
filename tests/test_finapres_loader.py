"""Tests for the Finapres CSV loader."""

from pathlib import Path
import pytest

from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal


# ── synthetic helpers ─────────────────────────────────────────────────────────

def _write_csv(path: Path, data_rows: list[str]) -> Path:
    """Write a minimal 8-line-header CSV with the given data rows."""
    header = (
        "NOVAScope : test\n"
        "Serial number : 000\n"
        "Hardware config : test\n"
        "Data within 10ms delta shares row\n"
        "Measurement;Reference;\n"
        '"2026-01-01_00.00.00";;;\n'
        "\n"
        "Time(sec);Signal(unit);\n"
    )
    path.write_text(header + "".join(data_rows), encoding="utf-8")
    return path


# ── detect_datetime_prefix ────────────────────────────────────────────────────

def test_detect_prefix_from_real_folder(csv_folder):
    prefix = detect_datetime_prefix(csv_folder)
    assert prefix == "2026-02-02_10.33.58"


def test_detect_prefix_empty_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        detect_datetime_prefix(tmp_path)


def test_detect_prefix_from_synthetic_folder(tmp_path):
    (tmp_path / "2025-01-01_12.00.00 HR.csv").write_text("x")
    prefix = detect_datetime_prefix(tmp_path)
    assert prefix == "2025-01-01_12.00.00"


# ── load_csv_signal ───────────────────────────────────────────────────────────

def test_missing_file_returns_none():
    assert load_csv_signal(Path("/nonexistent/signal.csv")) is None


def test_load_real_hr_signal(csv_folder):
    path = csv_folder / "2026-02-02_10.33.58 HR.csv"
    sig = load_csv_signal(path, name="HR", unit="bpm")
    assert sig is not None
    assert len(sig.times) > 0
    assert len(sig.times) == len(sig.values)
    assert sig.name == "HR"
    assert sig.unit == "bpm"


def test_load_real_rebap_signal(csv_folder):
    path = csv_folder / "2026-02-02_10.33.58 reBAP.csv"
    sig = load_csv_signal(path, name="reBAP", unit="mmHg")
    assert sig is not None
    assert len(sig.times) > 100_000  # reBAP is a 200 Hz waveform — expect many samples
    assert len(sig.times) == len(sig.values)


def test_times_values_always_same_length(csv_folder):
    """Arrays must be equal length regardless of which signal is loaded."""
    for name in ("HR", "reBAP", "ECG I"):
        path = csv_folder / f"2026-02-02_10.33.58 {name}.csv"
        if not path.exists():
            continue
        sig = load_csv_signal(path, name=name, unit="")
        assert len(sig.times) == len(sig.values), f"{name}: length mismatch"


def test_blank_value_row_skipped_atomically(tmp_path):
    """A row with a blank value field must be dropped entirely.

    Before the atomicity fix, float(parts[0]) would append to times but the
    subsequent ValueError on parts[1] left values one item short.
    """
    csv = _write_csv(tmp_path / "test.csv", [
        "1.0;100.5;\n",
        "2.0;;\n",        # blank value — must be skipped in full
        "3.0;200.5;\n",
    ])
    sig = load_csv_signal(csv, name="test", unit="u")
    assert sig is not None
    assert len(sig.times) == len(sig.values) == 2
    assert sig.times[0] == pytest.approx(1.0)
    assert sig.times[1] == pytest.approx(3.0)
    assert sig.values[0] == pytest.approx(100.5)
    assert sig.values[1] == pytest.approx(200.5)


def test_all_blank_values_returns_none(tmp_path):
    csv = _write_csv(tmp_path / "empty.csv", [
        "1.0;;\n",
        "2.0;;\n",
    ])
    assert load_csv_signal(csv) is None


def test_signal_bool_false_when_empty(tmp_path):
    csv = _write_csv(tmp_path / "empty.csv", [])
    assert not load_csv_signal(csv)
