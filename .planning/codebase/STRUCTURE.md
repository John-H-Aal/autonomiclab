# Codebase Structure

**Analysis Date:** 2026-04-26

## Directory Layout

```
AutonomicLab/
├── autonomiclab/                # Main Python package
│   ├── __init__.py              # __version__, __author__, __email__
│   ├── __main__.py              # Entry point: splash, login, MainWindow
│   ├── analysis/                # Pure signal processing per protocol
│   │   ├── __init__.py
│   │   ├── valsalva.py          # ValsalvaResult + ValsalvaAnalyzer
│   │   ├── deep_breathing.py    # RSACycle, DeepBreathingResult, DeepBreathingAnalyzer
│   │   └── stand.py             # StandResult, StandAnalyzer (placeholder)
│   ├── auth/                    # Authentication, encrypted user storage
│   │   ├── __init__.py          # (empty)
│   │   ├── crypto.py            # Fernet key derivation, MAC hash, HMAC sign/verify
│   │   ├── guest_counter.py     # GuestCounterStore — MAC-bound HMAC-signed counter
│   │   ├── models.py            # Role enum, User, GuestCounter dataclasses
│   │   ├── session.py           # Module-level singleton holding logged-in User
│   │   ├── sync.py              # GitHub Contents-API users.db pull
│   │   └── user_store.py        # UserStore — encrypted SQLite users
│   ├── config/                  # Settings + fonts
│   │   ├── __init__.py          # Re-exports FontLoader
│   │   ├── app_settings.py      # AppSettings (config.yaml + ~/.autonomiclab/settings.yaml)
│   │   ├── font_loader.py       # FontLoader — fonts.yaml + zoom
│   │   └── fonts.yaml           # Font sizes, weights, layout percentages
│   ├── core/                    # Domain models + file loading (Qt-free)
│   │   ├── __init__.py          # (empty)
│   │   ├── dataset_service.py   # DatasetService.load / load_nsc
│   │   ├── finapres_loader.py   # detect_datetime_prefix, load_csv_signal
│   │   ├── markers_handler.py   # load_markers, load_region_markers, determine_phase
│   │   ├── models.py            # Signal, Marker, Dataset
│   │   ├── nsc_reader.py        # NscReader for .nsc ZIP/.nsd binary
│   │   ├── overrides.py         # Atomic JSON persistence (load/save/_validate)
│   │   └── protocols.py         # BaselineOverrideCallback / PointOverrideCallback / CycleOverrideCallback
│   ├── export/                  # File output
│   │   ├── __init__.py
│   │   ├── excel.py             # ExcelExporter (openpyxl)
│   │   └── image.py             # ImageExporter (pyqtgraph PNG)
│   ├── gui/                     # PyQt6 widgets and orchestration
│   │   ├── __init__.py
│   │   ├── app_controller.py    # AppController + WindowProtocol
│   │   ├── app_state.py         # AppState dataclass
│   │   ├── close_mixin.py       # EscapeCloseMixin
│   │   ├── main_window.py       # MainWindow (View)
│   │   ├── raw_data_window.py   # RawDataWindow (multi-signal viewer + ECG)
│   │   ├── auth/                # Login + admin UIs
│   │   │   ├── __init__.py
│   │   │   ├── admin_panel.py
│   │   │   └── login_dialog.py
│   │   └── widgets/             # Reusable Qt widgets
│   │       ├── __init__.py
│   │       └── interactive_plot.py  # InteractivePlotWidget — pyqtgraph + snap-to-trace
│   ├── plotting/                # pyqtgraph drawing per protocol
│   │   ├── __init__.py
│   │   ├── deep_breathing.py    # DeepBreathingPlotter
│   │   ├── deep_breathing_cycles.py # CycleInteractor
│   │   ├── helpers.py           # Shared drawing primitives
│   │   ├── overview.py          # OverviewPlotter (full recording)
│   │   ├── registry.py          # PROTOCOL_REGISTRY + resolve_protocol
│   │   ├── stand.py             # StandPlotter
│   │   ├── valsalva.py          # ValsalvaPlotter
│   │   └── valsalva_baseline.py # BaselineRegionInteractor
│   └── utils/                   # Logger + small constants
│       ├── __init__.py          # Re-exports get_logger, configure_root_logger
│       ├── config.py            # APP_NAME / APP_VERSION (legacy)
│       └── logger.py            # configure_root_logger, get_logger
├── tests/                       # pytest suite
│   ├── conftest.py              # csv_folder / nsc_file fixtures (skip if data absent)
│   ├── __init__.py
│   ├── test_dataset_service.py
│   ├── test_finapres_loader.py
│   ├── test_guest_counter.py
│   ├── test_nsc_reader.py
│   └── test_user_store.py
├── scripts/                     # Operational scripts (not packaged)
│   ├── create_admin.py          # Seed first admin user in users.db
│   └── render_doc_screenshots.py
├── assets/                      # Bundled icons / splash
│   ├── autonomiclab.ico
│   ├── autonomiclab2.xcf
│   └── autonomiclab_splash.png
├── docs/                        # User-facing documentation
│   ├── figs/                    # Generated screenshots (PDF source images)
│   ├── user_guide.css
│   └── user_guide.md
├── data/                        # Real Finapres recordings (gitignored)
├── dist/                        # PyInstaller output (gitignored)
├── .github/workflows/release.yml # Tag-triggered Windows build
├── .planning/codebase/          # GSD codebase docs (this folder)
├── .claude/                     # Claude Code config + memory
├── autonomiclab.egg-info/       # setuptools metadata
├── venv/                        # Local virtualenv
├── BUILDING.md                  # Build / release instructions
├── CLAUDE.md                    # Project guide for Claude
├── INSTALLATION.md              # End-user install
├── LICENSE
├── README.md
├── build.ps1                    # PowerShell build helper
├── config.yaml                  # Admin config (committed sample)
├── create_assets.py             # Icon/splash generator
├── installer.iss                # Inno Setup installer script
├── pytest.ini                   # pytest config
├── requirements.txt             # Runtime deps
├── requirements-dev.txt         # Dev deps (pytest)
├── setup.py                     # setuptools install
├── autonomiclab.log             # Runtime log (gitignored)
├── guest_counter.json           # Per-machine guest counter (gitignored)
└── users.db                     # Encrypted SQLite user DB (gitignored)
```

## Directory Purposes

**`autonomiclab/`:**
- Purpose: The single Python package shipped to users.
- Contains: All production source code.
- Key files: `__main__.py` (entry), `__init__.py` (`__version__ = "1.0.31"`).

**`autonomiclab/core/`:**
- Purpose: Qt-free domain layer — models, file parsers, persistence helpers.
- Contains: Dataclasses (`Signal`, `Marker`, `Dataset`), CSV/binary loaders, override store, callback Protocols.
- Key files: `models.py`, `dataset_service.py`, `finapres_loader.py`, `nsc_reader.py`, `markers_handler.py`, `overrides.py`, `protocols.py`.

**`autonomiclab/analysis/`:**
- Purpose: Pure signal-processing algorithms; one file per protocol.
- Contains: `Analyzer` classes returning result dataclasses.
- Key files: `valsalva.py` (`ValsalvaAnalyzer` — Novak 2011), `deep_breathing.py` (`DeepBreathingAnalyzer` — RSA cycle detection), `stand.py` (placeholder).

**`autonomiclab/plotting/`:**
- Purpose: pyqtgraph rendering and interactive overlays per protocol.
- Contains: One `Plotter` per protocol, `helpers.py` shared primitives, `registry.py`, plus `*_baseline.py` / `*_cycles.py` interactor classes.
- Key files: `registry.py` (`PROTOCOL_REGISTRY`, `resolve_protocol`), `helpers.py` (`add_dot`, `add_draggable_dot`, `shade_region`, `add_marker_vlines`, `style_plot`, …), `overview.py` (full-recording).

**`autonomiclab/gui/`:**
- Purpose: PyQt6 widgets and the orchestration controller.
- Contains: `MainWindow` (View), `AppController` (orchestrator + `WindowProtocol`), `AppState` (mutable state), `RawDataWindow`, `EscapeCloseMixin`, login/admin sub-package, reusable widgets.
- Key files: `main_window.py`, `app_controller.py`, `app_state.py`, `widgets/interactive_plot.py`.

**`autonomiclab/auth/`:**
- Purpose: Login, encrypted user DB, guest counter, GitHub `users.db` sync.
- Contains: `UserStore` (Fernet+SQLite), `session` singleton, `GuestCounterStore`, `crypto` helpers, `sync` (Contents API), data models.
- Key files: `user_store.py`, `session.py`, `crypto.py`.

**`autonomiclab/config/`:**
- Purpose: Settings and fonts.
- Contains: `AppSettings` merging admin `config.yaml` and per-user prefs, `FontLoader` reading `fonts.yaml`.
- Key files: `app_settings.py`, `font_loader.py`, `fonts.yaml`.

**`autonomiclab/export/`:**
- Purpose: Output writers — Excel and PNG.
- Contains: `ExcelExporter`, `ImageExporter`.
- Key files: `excel.py`, `image.py`.

**`autonomiclab/utils/`:**
- Purpose: Logging and small constants.
- Contains: `configure_root_logger`, `get_logger`, legacy `APP_NAME`/`APP_VERSION`.
- Key files: `logger.py`.

**`tests/`:**
- Purpose: pytest suite for headless-testable layers (`core`, `auth`).
- Contains: One `test_*.py` per module under test, `conftest.py` with optional real-data fixtures.
- Key files: `conftest.py`, `test_dataset_service.py`, `test_nsc_reader.py`, `test_user_store.py`.

**`scripts/`:**
- Purpose: One-off operational scripts run outside the GUI.
- Contains: `create_admin.py` (interactive admin seed), `render_doc_screenshots.py`.

**`assets/`:**
- Purpose: Static binary assets bundled by PyInstaller / Inno Setup.
- Contains: `autonomiclab.ico` (Windows icon), `autonomiclab_splash.png`, `autonomiclab2.xcf` (GIMP source).

**`docs/`:**
- Purpose: End-user PDF/Markdown user guide.
- Contains: `user_guide.md`, `user_guide.css` (WeasyPrint), `figs/` (generated PNG screenshots).

**`data/`:**
- Purpose: Real Finapres recordings used by tests.
- Generated: No — placed manually by developers.
- Committed: No (gitignored).

**`dist/`:**
- Purpose: PyInstaller output.
- Generated: Yes (`build.ps1` / GitHub Actions).
- Committed: No (gitignored).

**`.github/workflows/`:**
- Purpose: CI definitions.
- Contains: `release.yml` — Windows build triggered by `v*` tags.

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis docs (consumed by `/gsd-plan-phase`).
- Contains: `ARCHITECTURE.md`, `STRUCTURE.md`, plus any others written by the mapper.

## Key File Locations

**Entry Points:**
- `autonomiclab/__main__.py`: `python -m autonomiclab` boot — splash, logger, login, `MainWindow`.
- `autonomiclab/gui/main_window.py:503` — developer-only direct `MainWindow` launch (skips login).
- `scripts/create_admin.py`: Seed first admin in `users.db`.

**Configuration:**
- `config.yaml` (project root, also placed next to `AutonomicLab.exe`): admin settings — `data_folder`, `users_db_token`, `allow_guest`.
- `~/.autonomiclab/settings.yaml`: per-user prefs (data folder, UI zoom).
- `autonomiclab/config/fonts.yaml`: font sizes, weights, left-panel width percent.
- `pytest.ini`: pytest configuration.
- `setup.py`: setuptools install (entry point `autonomiclab=autonomiclab.__main__:main`).
- `requirements.txt`, `requirements-dev.txt`: pip dependencies.

**Core Logic:**
- `autonomiclab/gui/app_controller.py`: orchestration (`load_dataset`, `load_nsc_file`, `plot_current_phase`, `on_*_override`, `export_current`, `_save_overrides`).
- `autonomiclab/gui/main_window.py`: View — widget construction and `WindowProtocol` UI-update methods.
- `autonomiclab/core/dataset_service.py`: dataset assembly from disk.
- `autonomiclab/core/finapres_loader.py`: Finapres CSV parsing — atomic `(t, v)` pair parsing.
- `autonomiclab/core/nsc_reader.py`: Finapres NOVA `.nsc` (ZIP of `.nsd`) binary reader.
- `autonomiclab/core/overrides.py`: atomic JSON override persistence.
- `autonomiclab/plotting/registry.py`: protocol → analyzer + plotter lookup.
- `autonomiclab/auth/user_store.py`: encrypted SQLite users.

**Testing:**
- `tests/conftest.py`: `csv_folder` and `nsc_file` fixtures (skip if `data/` absent).
- `tests/test_*.py`: one per module, headless (no PyQt6 imports).

**Build / Release:**
- `.github/workflows/release.yml`: Windows `.exe` build on `v*` tag push.
- `installer.iss`: Inno Setup installer script.
- `build.ps1`: local PowerShell build helper.
- `BUILDING.md`: build instructions.
- `create_assets.py`: regenerate icon/splash.

## Naming Conventions

**Files:**
- All Python source: `snake_case.py`. One protocol per file in both `analysis/` and `plotting/` (`valsalva.py`, `deep_breathing.py`, `stand.py`).
- Per-protocol interactor classes get a suffix in `plotting/`: `valsalva_baseline.py`, `deep_breathing_cycles.py`.
- Test files mirror the source under test: `test_<module>.py` in `tests/`.
- Config: lowercase YAML (`config.yaml`, `fonts.yaml`).

**Directories:**
- Lowercase `snake_case`. Modules use single-word names where possible (`auth`, `core`, `gui`, `utils`).
- Sub-packages mirror feature areas (`gui/auth/`, `gui/widgets/`).

**Classes:**
- `PascalCase`. Pattern: `<Protocol>Analyzer`, `<Protocol>Plotter`, `<Protocol>Result` (e.g. `ValsalvaAnalyzer`, `DeepBreathingPlotter`, `StandResult`).
- Interactors named `<Thing>Interactor` (`BaselineRegionInteractor`, `CycleInteractor`).
- Stores named `<Thing>Store` (`UserStore`, `GuestCounterStore`).

**Functions / variables:**
- `snake_case`. Module-private with leading underscore (`_FILL`, `_TICK_S`, `_app_dir`, `_validate`).
- Module-level constants: `UPPER_SNAKE_CASE` (`_DEFAULT_LAUNCHES`, `_FILENAME`, `N_SELECT`, `_NSC_SIGNALS`).

**Logger:**
- Always `log = get_logger(__name__)` at module top (after stdlib imports). Never `logging.getLogger(...)` directly except inside `utils/logger.py`.

## Where to Add New Code

**New protocol (e.g. "head-up tilt"):**
- Analyzer: `autonomiclab/analysis/<name>.py` — define `<Name>Result` dataclass and `<Name>Analyzer.analyze(dataset, markers, **kwargs) -> <Name>Result`.
- Plotter: `autonomiclab/plotting/<name>.py` — `<Name>Plotter.plot(plot_widget, dataset, result, t_start, t_end, **callbacks)` and `.export(plot_widget, result, output_dir, mode)`.
- Register: add an entry to `PROTOCOL_REGISTRY` and a keyword to `_KEYWORDS` in `autonomiclab/plotting/registry.py`.
- Wire callbacks (if interactive): add a Protocol type in `autonomiclab/core/protocols.py`, add `on_<name>_override` to `AppController`, and pass it as a `plot_kwargs` lambda in `AppController.plot_current_phase`.
- Tests: `tests/test_<name>_analyzer.py`.

**New domain feature (loader, model, persistence):**
- Implementation: `autonomiclab/core/<name>.py`.
- Tests: `tests/test_<name>.py`. Keep Qt-free.

**New analysis algorithm:**
- Implementation: `autonomiclab/analysis/<name>.py`.
- Pure numpy/scipy. Return a `@dataclass` result.
- Tests: `tests/test_<name>.py`.

**New GUI widget:**
- Reusable widget: `autonomiclab/gui/widgets/<name>.py` — subclass appropriate Qt or pyqtgraph base.
- Dialog/window: `autonomiclab/gui/<name>_window.py` or `autonomiclab/gui/<name>_dialog.py`. Apply `EscapeCloseMixin` for consistent close behaviour.

**New auth feature:**
- Implementation: `autonomiclab/auth/<name>.py`.
- If it touches `users.db`, extend `UserStore`. If it touches secrets, route through `autonomiclab/auth/crypto.py`.

**New config option:**
- Reader: add a `@property` on `AppSettings` (`autonomiclab/config/app_settings.py`).
- Documentation: update `config.yaml` sample with a commented default.

**New export format:**
- Implementation: `autonomiclab/export/<format>.py` — class with one method per result type.
- Wire: call from the corresponding `<Protocol>Plotter.export(...)` method.

**Utilities / shared helpers:**
- Plotting primitives: append to `autonomiclab/plotting/helpers.py`.
- Cross-cutting helpers: `autonomiclab/utils/<name>.py`. Avoid creating new sub-packages for one-off utilities.

**Operational scripts (not shipped to users):**
- `scripts/<name>.py`. Top-line `sys.path.insert(0, str(Path(__file__).parent.parent))` to allow running from project root.

## Special Directories

**`venv/`:**
- Purpose: Local Python virtualenv.
- Generated: Yes (manually, `python -m venv venv`).
- Committed: No (gitignored).

**`autonomiclab.egg-info/`:**
- Purpose: setuptools editable-install metadata.
- Generated: Yes (`pip install -e .`).
- Committed: Visible in tree but should not be edited.

**`dist/`:**
- Purpose: PyInstaller output (`AutonomicLab.exe` + `config.yaml` + `autonomiclab_splash.png`).
- Generated: Yes (CI on tag push).
- Committed: No (gitignored).

**`data/`:**
- Purpose: Real Finapres recordings for manual testing and pytest fixtures.
- Generated: No — manually populated.
- Committed: No (gitignored).

**`assets/`:**
- Purpose: Source images bundled by PyInstaller and Inno Setup.
- Generated: Optionally regenerated by `create_assets.py`.
- Committed: Yes.

**`docs/figs/`:**
- Purpose: Screenshots embedded in `user_guide.md` / generated PDF.
- Generated: Yes (`scripts/render_doc_screenshots.py`).
- Committed: Yes (since v1.0.29 — moved into `docs/` for PDF generation).

**`.planning/`:**
- Purpose: GSD planning artifacts (codebase docs, phase plans).
- Generated: By GSD commands.
- Committed: Yes (codebase docs); phase-specific files may be ignored.

**Runtime files in project root:**
- `autonomiclab.log`: Runtime log (gitignored).
- `users.db`: Encrypted SQLite user DB (gitignored, synced via GitHub).
- `guest_counter.json`: Per-machine HMAC-signed guest counter (gitignored).
- `config.yaml`: Admin config (gitignored — committed sample only as a template; see `.gitignore`).

---

*Structure analysis: 2026-04-26*
