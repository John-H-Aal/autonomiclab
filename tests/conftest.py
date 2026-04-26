"""Shared fixtures and data paths for all tests."""

from pathlib import Path
import pytest

# Paths to real data — gitignored, so only present on dev machines.
# Tests that use these fixtures skip automatically when data is absent.
DATA_ROOT    = Path(__file__).parent.parent / "data"
CSV_FOLDER   = DATA_ROOT / "2026-02-02_10.33.58"
NSC_FILE     = DATA_ROOT / "2026-04-24_1224 NOVA recordings" / "12091FR_2026-04-20_08.49.09.nsc"


@pytest.fixture(scope="session")
def csv_folder():
    if not CSV_FOLDER.exists():
        pytest.skip("Real CSV data not present (data/ is gitignored)")
    return CSV_FOLDER


@pytest.fixture(scope="session")
def nsc_file():
    if not NSC_FILE.exists():
        pytest.skip("Real NSC data not present (data/ is gitignored)")
    return NSC_FILE
