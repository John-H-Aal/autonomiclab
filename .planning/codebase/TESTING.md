# Testing Patterns

**Analysis Date:** 2026-04-26

## Test Framework

**Runner:**
- `pytest >= 8.0` (declared in `requirements-dev.txt`)
- Installed version: `pytest-9.0.3` (verified by `pytest --collect-only`)
- Config: `pytest.ini` (3 lines):
  ```ini
  [pytest]
  testpaths = tests
  addopts = -v --tb=short
  ```

**Assertion library:**
- Plain `assert` statements with pytest's rewriting
- `pytest.approx` for float tolerance comparisons
- `pytest.raises(...)` context manager for expected-exception tests
- `numpy.testing.assert_array_equal` for ndarray equality (`tests/test_nsc_reader.py:114`)

**Run commands:**
```bash
source venv/bin/activate
python -m pytest                          # Run all tests (verbose, short tracebacks)
python -m pytest tests/test_nsc_reader.py # Run one module
python -m pytest -k "guest"               # Filter by name
python -m pytest --collect-only           # List without running
```

No coverage tool is installed; no watch-mode runner is configured.

## Test File Organization

**Location:** Centralized under `tests/` at repo root — **not** co-located with source.

**Naming:** `test_<module>.py` — one test module per source module being tested.

**Current tests directory** (`tests/`):
```
tests/
├── __init__.py                     # 1-line stub: "# Tests module"
├── conftest.py                     # Shared fixtures (data path skips)
├── test_dataset_service.py         # Integration: CSV + NSC load paths
├── test_finapres_loader.py         # Unit: CSV parser
├── test_guest_counter.py           # Unit: HMAC-signed launch counter
├── test_nsc_reader.py              # Unit: .nsc binary reader
└── test_user_store.py              # Unit: encrypted SQLite user DB
```

**Coverage:** 59 tests across 5 modules covering only the **non-Qt** layers:
- `core/` (loaders, dataset service, NSC reader)
- `auth/` (user store, guest counter)

**No tests for:** `gui/`, `plotting/`, `analysis/`, `export/`, `config/`, `utils/`.

## Test Structure

**Suite organization** — files use ASCII section dividers to group related tests:

```python
"""Tests for the Finapres CSV loader."""

from pathlib import Path
import pytest

from autonomiclab.core.finapres_loader import detect_datetime_prefix, load_csv_signal


# ── synthetic helpers ─────────────────────────────────────────────────────────

def _write_csv(path: Path, data_rows: list[str]) -> Path:
    ...


# ── detect_datetime_prefix ────────────────────────────────────────────────────

def test_detect_prefix_from_real_folder(csv_folder):
    prefix = detect_datetime_prefix(csv_folder)
    assert prefix == "2026-02-02_10.33.58"
```
Reference: `tests/test_finapres_loader.py:1-31`.

**Patterns:**
- Module docstring at top (one line) describes what's under test
- Test functions are flat — no test classes
- One assertion per test where practical; multiple assertions allowed when they describe one logical state (e.g., `test_load_real_hr_signal` checks 4 properties of the same return value, `tests/test_finapres_loader.py:51-58`)
- Test names are full sentences: `test_blank_value_row_skipped_atomically`, `test_tampered_remaining_resets_to_zero`, `test_inactive_user_cannot_authenticate`
- Synthetic helper functions are `_`-prefixed at module scope (e.g., `_write_csv`, `_user`) and are not collected by pytest
- Section dividers `# ── name ──...` separate logical test groups within a file

## Fixtures

**Shared fixtures live in `tests/conftest.py`:**

```python
DATA_ROOT  = Path(__file__).parent.parent / "data"
CSV_FOLDER = DATA_ROOT / "2026-02-02_10.33.58"
NSC_FILE   = DATA_ROOT / "2026-04-24_1224 NOVA recordings" / "12091FR_2026-04-20_08.49.09.nsc"

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
```
Reference: `tests/conftest.py:1-25`.

**Fixture scopes used:**
- `scope="session"` — for read-only paths to gitignored real data (`csv_folder`, `nsc_file`)
- `scope="module"` — for expensive-to-construct objects shared across all tests in one file (`reader` in `test_nsc_reader.py:18`, `svc` in `test_dataset_service.py:9`)
- default function scope — for objects that need a fresh state per test (`store` in `test_user_store.py:11`, `counter_path` / `store` in `test_guest_counter.py:10-17`)

**`tmp_path` is the standard scratch directory:**
Used for any test that needs to write files (`test_user_store.py:13` for SQLite DB, `test_guest_counter.py:11` for JSON, `test_finapres_loader.py:39` for synthetic CSV). Never write to real paths from tests.

**Skip-when-data-absent pattern:**
Real Finapres recordings are >100 MB and `gitignored`. The session-scoped fixtures call `pytest.skip(...)` when the data is missing, so CI (no data) and dev machines (data present) both pass. Tests that do NOT take `csv_folder` / `nsc_file` parameters always run.

## Mocking

**No mocks.** No use of `unittest.mock`, `pytest-mock`, `monkeypatch`, or stubs anywhere in the test suite.

The strategy is instead:
1. **Real data** for I/O-heavy modules (`csv_folder`, `nsc_file` fixtures point to actual recordings)
2. **Synthetic on-disk fixtures** for parser edge cases — see `_write_csv` helper in `tests/test_finapres_loader.py:11-24` which writes a minimal 8-line-header CSV to `tmp_path` so the loader's real file-reading code path is exercised against a controlled input
3. **Real SQLite + real cryptography** for `UserStore` tests — encryption round-trip is verified end-to-end (`test_encrypted_roundtrip` in `tests/test_user_store.py:82-89`)

**What to mock:** Nothing currently. If a future test needs to mock something (e.g., the Dropbox sync HTTP call in `auth/sync.py`), introduce `pytest-mock` and document it here.

**What NOT to mock:** Filesystem (use `tmp_path`), database engines (use in-tmp sqlite), cryptographic primitives (they're fast enough to run for real).

## Fixtures and Factories

**Lightweight factory functions** are used in place of fixture explosions when several variants of an object are needed:

```python
def _user(username="alice", role=Role.INVESTIGATOR, active=True) -> User:
    return User(
        username=username,
        display_name=username.title(),
        password_hash=UserStore.hash_password("secret123"),
        role=role,
        is_active=active,
    )
```
Reference: `tests/test_user_store.py:16-23`. Pattern: keyword arguments with sensible defaults, `_`-prefixed name so pytest doesn't collect it.

**Fixture data location:** No `tests/fixtures/` directory exists. Real recordings live under `<repo>/data/` (gitignored). Synthetic test inputs are constructed in-process and written to `tmp_path`.

## Coverage

**Requirements:** None enforced.
**Tooling:** No `coverage.py`, no `pytest-cov`, no CI gate.

**Inferred coverage by area:**
| Area | Coverage |
|------|----------|
| `core/finapres_loader.py` | High (parser edge cases tested) |
| `core/nsc_reader.py` | High (binary format + ground-truth values) |
| `core/dataset_service.py` | Integration paths covered (CSV and NSC) |
| `core/markers_handler.py`, `core/overrides.py`, `core/protocols.py`, `core/models.py` | None |
| `auth/user_store.py`, `auth/guest_counter.py` | High |
| `auth/crypto.py`, `auth/sync.py`, `auth/session.py`, `auth/models.py` | Indirect only |
| `analysis/*` | None |
| `plotting/*` | None |
| `gui/*` | None — see "Headless test setup" below |
| `export/*` | None |
| `config/*`, `utils/*` | None |

## Test Types

**Unit tests:**
- `test_finapres_loader.py` — exercises `detect_datetime_prefix` and `load_csv_signal` against synthetic CSVs in `tmp_path`. Targets atomic `(t, v)` parsing edge case (the historical desync bug).
- `test_user_store.py` — exercises `UserStore` add/get/list/authenticate/update/delete + encryption round-trip.
- `test_guest_counter.py` — exercises `GuestCounterStore` initial state, decrement, persistence, tamper detection (HMAC).
- `test_nsc_reader.py` — structural (channels, context manager) + physical-value (HR ≈ 71.2 bpm, fiSYS ≈ 125.6, fiDIA ≈ 79.0) + gap-mask correctness against real `.nsc` recording from exam 12091FR.

**Integration tests:**
- `test_dataset_service.py` — full `DatasetService.load(folder)` and `.load_nsc(file)` paths, verifying `Dataset.signals`, `Dataset.markers`, `Dataset.region_markers`, and `Dataset.phase_window(...)`.

**E2E / GUI tests:** **None exist.**

## Headless Test Setup — STATUS: NOT IMPLEMENTED

**From `CLAUDE.md`:**
> UI cannot be tested without running the app — no headless Qt test setup exists.

What this means in practice:
- `pytest-qt` is **not installed** (not in `requirements-dev.txt`)
- No `xvfb` / Xvfb session orchestration in CI
- `MainWindow`, `AppController`, all `*Plotter` classes, all dialogs (`LoginDialog`, `AdminPanel`), and all interactive widgets (`InteractivePlotWidget`, `BaselineRegionInteractor`, `CycleInteractor`) are **untested**
- The pyqtgraph stale-C++-object bugs (suppressed in `__main__._install_exception_hook`, `autonomiclab/__main__.py:21-36`) cannot be regression-tested

**Implications when adding new code:**
- Anything in `gui/` or `plotting/` ships untested. Manual smoke-test by running `python -m autonomiclab` against a real dataset before committing.
- Pure-logic helpers MUST be extracted out of widgets so they can be unit-tested. Pattern: put algorithms in `analysis/` (no Qt imports) and call them from `plotting/`. Currently followed — keep it that way.
- A future headless setup would need `pytest-qt` plus `QT_QPA_PLATFORM=offscreen`. This has not been attempted.

## Common Patterns

**Async testing:** Not applicable — the codebase is synchronous.

**Error testing:**
```python
def test_csv_missing_folder_raises(svc):
    with pytest.raises(FileNotFoundError):
        svc.load(Path("/nonexistent/folder"))

def test_unknown_channel_raises(reader):
    with pytest.raises(KeyError):
        reader.read("NOT_A_CHANNEL")
```
Reference: `tests/test_dataset_service.py:38-40`, `tests/test_nsc_reader.py:31-33`.

**Float comparisons** — always `pytest.approx`:
```python
assert sig.times[0] == pytest.approx(1.0)
assert float(np.median(valid)) == pytest.approx(71.2, abs=5.0)
```
Reference: `tests/test_finapres_loader.py:93`, `tests/test_nsc_reader.py:86`.

**Numpy array invariants:**
```python
assert len(sig.times) == len(sig.values)            # length parity
assert np.all(np.diff(sig.times) >= 0)              # monotonic
np.testing.assert_array_equal(np.isnan(sig.values), mask)
```
Reference: `tests/test_nsc_reader.py:56-64, 110-114`.

**Persistence round-trip:**
Tests that a side-effect persists across object reconstruction:
```python
def test_persists_across_instances(counter_path):
    GuestCounterStore(counter_path).consume()
    assert GuestCounterStore(counter_path).remaining() == 9

def test_encrypted_roundtrip(tmp_path):
    db = tmp_path / "roundtrip.db"
    UserStore(db).add_user(_user())
    u = UserStore(db).get_user("alice")
    assert u is not None
```
Reference: `tests/test_guest_counter.py:53-55`, `tests/test_user_store.py:82-89`.

**Tamper / invariant detection:**
The HMAC-signed guest counter has explicit tests for what happens when the file is hand-edited (`test_tampered_remaining_resets_to_zero` in `tests/test_guest_counter.py:60-70`). Use this pattern when adding any other signed/encrypted on-disk format.

## Adding New Tests

**For a new pure-logic module:**
1. Create `tests/test_<module>.py`
2. Module-level docstring describing scope
3. Fixtures with `tmp_path` for any I/O
4. Group tests with `# ── section ──...` dividers
5. Use full-sentence test names

**For tests that need real recordings:**
1. Add the fixture to `tests/conftest.py` with `pytest.skip` when missing
2. Use `scope="session"` so multiple tests share the same path resolution
3. Document the ground-truth values in the test module docstring (see `tests/test_nsc_reader.py:1-7`)

**For Qt/GUI code:**
Currently not testable in CI. Either extract logic to a non-Qt module and test that, or accept manual verification.

---

*Testing analysis: 2026-04-26*
