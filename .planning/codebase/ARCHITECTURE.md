<!-- refreshed: 2026-04-26 -->
# Architecture

**Analysis Date:** 2026-04-26

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                       Entry Point                                     │
│   `autonomiclab/__main__.py` — splash, logging, login, MainWindow     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       GUI Layer (PyQt6)                              │
├──────────────────┬─────────────────────┬─────────────────────────────┤
│   MainWindow     │   AppController     │      AppState               │
│ `gui/main_window`│ `gui/app_controller`│   `gui/app_state.py`        │
│  (View, widget   │  (Orchestrator,     │   (Mutable shared state:    │
│   construction,  │  load → analyse →   │    dataset, overrides,      │
│   UI updates via │  plot → persist →   │    last_protocol_key,       │
│   WindowProtocol)│   export)           │    analysis_mode)           │
└────────┬─────────┴──────────┬──────────┴──────────┬──────────────────┘
         │                    │                     │
         │                    ▼                     │
         │   ┌────────────────────────────────────┐ │
         │   │    Protocol Registry (lookup)      │ │
         │   │   `plotting/registry.py`           │ │
         │   │   phase keyword → analyzer+plotter │ │
         │   └────────┬──────────────────┬────────┘ │
         │            │                  │          │
         │            ▼                  ▼          │
         │   ┌──────────────┐   ┌────────────────┐  │
         │   │  Analysis    │   │   Plotting     │  │
         │   │ `analysis/`  │   │  `plotting/`   │  │
         │   │ valsalva,    │   │ valsalva,      │  │
         │   │ deep_breath, │   │ deep_breathing,│  │
         │   │ stand        │   │ stand, overview│  │
         │   └──────┬───────┘   └────────┬───────┘  │
         │         │                     │          │
         ▼         ▼                     ▼          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Core / Domain                                   │
│   `core/dataset_service.py` — loads .fef CSV folder or .nsc binary   │
│   `core/finapres_loader.py` — Finapres CSV parser                    │
│   `core/nsc_reader.py`      — NOVA .nsc ZIP/.nsd binary reader       │
│   `core/markers_handler.py` — Markers.csv + RegionMarkers.csv        │
│   `core/models.py`          — Signal, Marker, Dataset                │
│   `core/overrides.py`       — atomic JSON persistence per dataset    │
│   `core/protocols.py`       — callback Protocols (typing)            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│   Cross-cutting:  auth/  config/  export/  utils/                    │
│                                                                       │
│   auth/    — UserStore (encrypted SQLite), session, guest_counter,   │
│              GitHub Contents-API users.db sync, Fernet crypto         │
│   config/  — AppSettings (config.yaml + ~/.autonomiclab/settings.yaml)│
│              FontLoader (fonts.yaml)                                  │
│   export/  — ExcelExporter (openpyxl), ImageExporter (pyqtgraph PNG)  │
│   utils/   — get_logger, configure_root_logger                        │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│   Filesystem outputs:                                                 │
│   • `<dataset>/overrides.json`  (atomic write via .tmp + os.replace)  │
│   • `<dataset>/results/*_<protocol>_<stamp>_<mode>.xlsx`              │
│   • `autonomiclab.log` (next to .exe / project root)                  │
│   • `users.db` synced ↔ private GitHub repo `autonomiclab-users`      │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Entry point | Splash, logger, exception hook, login flow, MainWindow boot | `autonomiclab/__main__.py` |
| MainWindow | Widget construction, UI-update methods (View) | `autonomiclab/gui/main_window.py` |
| AppController | Orchestration: load → analyse → plot → persist → export | `autonomiclab/gui/app_controller.py` |
| AppState | Single source of truth for mutable runtime state | `autonomiclab/gui/app_state.py` |
| InteractivePlotWidget | pyqtgraph layout with right-click snap-to-trace markers | `autonomiclab/gui/widgets/interactive_plot.py` |
| RawDataWindow | Multi-signal viewer (BP/HR/PAirway/ECG leads) | `autonomiclab/gui/raw_data_window.py` |
| Protocol Registry | phase keyword → `{analyzer, plotter}` lookup | `autonomiclab/plotting/registry.py` |
| DatasetService | Loads CSV folder or `.nsc` file → `Dataset` | `autonomiclab/core/dataset_service.py` |
| FinapresLoader | Parses `<prefix> <signal>.csv` into `Signal` (atomic t/v pairs) | `autonomiclab/core/finapres_loader.py` |
| NscReader | Parses `.nsc` ZIP of `.nsd` binary into `Signal` | `autonomiclab/core/nsc_reader.py` |
| MarkersHandler | Parses `Markers.csv` + `RegionMarkers.csv` | `autonomiclab/core/markers_handler.py` |
| OverrideStore | Atomic JSON persistence of manual overrides per dataset | `autonomiclab/core/overrides.py` |
| Domain models | `Signal`, `Marker`, `Dataset` dataclasses | `autonomiclab/core/models.py` |
| Callback Protocols | Structural typing for interactive plotter callbacks | `autonomiclab/core/protocols.py` |
| ValsalvaAnalyzer/Plotter | Novak 2011 Valsalva measurements + draggable baseline + dots | `autonomiclab/analysis/valsalva.py`, `autonomiclab/plotting/valsalva.py`, `autonomiclab/plotting/valsalva_baseline.py` |
| DeepBreathingAnalyzer/Plotter | RSA cycle detection + interactive cycle editor | `autonomiclab/analysis/deep_breathing.py`, `autonomiclab/plotting/deep_breathing.py`, `autonomiclab/plotting/deep_breathing_cycles.py` |
| StandAnalyzer/Plotter | Two-panel BP+HR plot (no numerical analysis yet) | `autonomiclab/analysis/stand.py`, `autonomiclab/plotting/stand.py` |
| OverviewPlotter | Three-panel BP/HR/PAirway full-recording overview | `autonomiclab/plotting/overview.py` |
| Plot helpers | Shared pyqtgraph drawing primitives | `autonomiclab/plotting/helpers.py` |
| AppSettings | `config.yaml` + per-user prefs merged view | `autonomiclab/config/app_settings.py` |
| FontLoader | `fonts.yaml` font/size/zoom registry | `autonomiclab/config/font_loader.py` |
| UserStore | Fernet-encrypted SQLite users table | `autonomiclab/auth/user_store.py` |
| Session | Module-level singleton holding the logged-in `User` | `autonomiclab/auth/session.py` |
| GuestCounterStore | MAC-bound HMAC-signed JSON launch counter | `autonomiclab/auth/guest_counter.py` |
| users.db sync | GitHub Contents-API pull of `users.db` | `autonomiclab/auth/sync.py` |
| Crypto | PBKDF2-derived Fernet key, MAC hash, HMAC sign/verify | `autonomiclab/auth/crypto.py` |
| LoginDialog/AdminPanel | Login + user management UIs | `autonomiclab/gui/auth/login_dialog.py`, `autonomiclab/gui/auth/admin_panel.py` |
| ExcelExporter | Formatted xlsx output for Valsalva/Deep Breathing | `autonomiclab/export/excel.py` |
| ImageExporter | PNG export of pyqtgraph scenes/plots | `autonomiclab/export/image.py` |
| Logger | Centralised root logger (stream + file) | `autonomiclab/utils/logger.py` |

## Pattern Overview

**Overall:** Layered MVC-ish desktop architecture with a Strategy/Registry pattern for protocols.

- **View (passive):** `MainWindow` is a `QMainWindow` reduced to widget construction and a small set of UI-update methods.
- **Controller:** `AppController` owns all orchestration. It calls back into the view only through the structural `WindowProtocol` defined in `autonomiclab/gui/app_controller.py` (lines 40–54), which keeps the import graph acyclic at runtime.
- **Model:** `AppState` (`autonomiclab/gui/app_state.py`) is a `@dataclass` holding the live `Dataset`, override map, last protocol key, last analyzer result, and analysis mode. Both view and controller hold a reference and mutate the same instance.
- **Domain core:** `core/` is Qt-free, pure-Python data loading and dataclasses. Analysis (`analysis/`) is also Qt-free signal processing returning result dataclasses.
- **Strategy via registry:** `PROTOCOL_REGISTRY` in `autonomiclab/plotting/registry.py` maps a string protocol key (`"valsalva"`, `"stand"`, `"deep breath"`) to an `{"analyzer": <Analyzer>, "plotter": <Plotter>}` pair. `resolve_protocol(phase_name)` does keyword matching on the region name.

**Key Characteristics:**
- One-way data flow: filesystem → `Dataset` → analyzer → result dataclass → plotter → pyqtgraph scene; user edits round-trip through `on_*_override` callbacks → `AppState.overrides` → `overrides.json` → re-plot.
- Analyzers and plotters are paired and stateless (instances held in the registry); per-call state lives in their result dataclass and the plotter's interactor objects.
- Interactor classes (`BaselineRegionInteractor`, `CycleInteractor`) own *all* mutable widget state for one interactive feature, so the plotter never reaches into pyqtgraph items by name.
- Auth is a pluggable cross-cut: `session._current_user` is the only module-global; admin gating is `if auth_session.is_admin():` in `MainWindow._init_menu_bar` (`autonomiclab/gui/main_window.py:297`).

## Layers

**Presentation (`autonomiclab/gui/`):**
- Purpose: Qt widgets, user input handling, visual feedback only.
- Location: `autonomiclab/gui/`
- Contains: `main_window.py`, `app_controller.py`, `app_state.py`, `raw_data_window.py`, `close_mixin.py`, `widgets/interactive_plot.py`, `auth/login_dialog.py`, `auth/admin_panel.py`.
- Depends on: `core`, `analysis`, `plotting`, `auth`, `config`, `export`, `utils`.
- Used by: `__main__.py`.

**Plotting (`autonomiclab/plotting/`):**
- Purpose: pyqtgraph rendering and interactive overlays for each protocol.
- Location: `autonomiclab/plotting/`
- Contains: per-protocol `*.py` plotters, `helpers.py` drawing primitives, `registry.py`, plus interactor classes (`valsalva_baseline.py`, `deep_breathing_cycles.py`).
- Depends on: `analysis` (for result types), `core` (`Dataset`, `Signal`, callback Protocols), pyqtgraph, openpyxl (via `export.excel`).
- Used by: `gui.app_controller`.

**Analysis (`autonomiclab/analysis/`):**
- Purpose: Pure signal-processing algorithms per protocol; produces result dataclasses.
- Location: `autonomiclab/analysis/`
- Contains: `valsalva.py` (`ValsalvaResult`, `ValsalvaAnalyzer`), `deep_breathing.py` (`RSACycle`, `DeepBreathingResult`, `DeepBreathingAnalyzer`), `stand.py` (placeholder).
- Depends on: `core.models`, numpy, scipy.
- Used by: `plotting.registry`, `gui.app_controller`.

**Core / Domain (`autonomiclab/core/`):**
- Purpose: File loading, parsing, and domain types. No Qt imports.
- Location: `autonomiclab/core/`
- Contains: `models.py`, `dataset_service.py`, `finapres_loader.py`, `nsc_reader.py`, `markers_handler.py`, `overrides.py`, `protocols.py`.
- Depends on: numpy, stdlib only.
- Used by: every other layer.

**Auth (`autonomiclab/auth/`):**
- Purpose: Authentication, encrypted user storage, guest counter, GitHub sync.
- Location: `autonomiclab/auth/`
- Contains: `models.py` (`Role`, `User`, `GuestCounter`), `crypto.py`, `user_store.py` (SQLite + Fernet), `session.py` (singleton), `guest_counter.py`, `sync.py`.
- Depends on: `cryptography`, `bcrypt`, stdlib `sqlite3`/`urllib`.
- Used by: `__main__`, `gui.main_window`, `gui.auth.*`.

**Config (`autonomiclab/config/`):**
- Purpose: Settings and font loading.
- Location: `autonomiclab/config/`
- Contains: `app_settings.py`, `font_loader.py`, `fonts.yaml`.
- Depends on: PyYAML, stdlib.
- Used by: `gui`, `__main__`.

**Export (`autonomiclab/export/`):**
- Purpose: Excel and PNG output.
- Location: `autonomiclab/export/`
- Contains: `excel.py` (`ExcelExporter`), `image.py` (`ImageExporter`).
- Depends on: openpyxl, Pillow (transitively), pyqtgraph (PNG export).
- Used by: per-protocol plotters via their `.export(...)` method (called by `AppController.export_current`, `autonomiclab/gui/app_controller.py:281`).

**Utils (`autonomiclab/utils/`):**
- Purpose: Logger and small constants.
- Location: `autonomiclab/utils/`
- Contains: `logger.py`, `config.py` (`APP_NAME`, `APP_VERSION` legacy constants).
- Depends on: stdlib.
- Used by: every module.

## Data Flow

### Primary Request Path — open dataset and analyse a phase

1. User clicks **Open Dataset** → `MainWindow._open_dataset` (`autonomiclab/gui/main_window.py:342`) shows a CSV-folder vs `.nsc`-file chooser.
2. CSV branch: `AppController.load_dataset(folder)` (`autonomiclab/gui/app_controller.py:84`) calls `DatasetService.load(folder)` (`autonomiclab/core/dataset_service.py:53`).
3. `DatasetService` calls `detect_datetime_prefix` (`autonomiclab/core/finapres_loader.py:16`), then `load_csv_signal` per known signal (`autonomiclab/core/finapres_loader.py:43`), then `load_markers` + `load_region_markers` (`autonomiclab/core/markers_handler.py:25`, `:61`).
4. Returns a `Dataset` (`autonomiclab/core/models.py:60`); `AppController` stores it in `AppState.dataset`, then loads any persisted overrides via `override_store.load(dataset.path)` (`autonomiclab/core/overrides.py:51`).
5. UI is refreshed via `WindowProtocol`: `populate_phase_combo`, `update_dataset_info`, `update_markers_table`, then `plot_current_phase()` (`autonomiclab/gui/app_controller.py:145`).
6. `plot_current_phase` reads the current phase from `MainWindow.get_current_phase()`, calls `resolve_protocol(phase)` (`autonomiclab/plotting/registry.py:51`), looks up `{analyzer, plotter}` in `PROTOCOL_REGISTRY`, calls `analyzer.analyze(dataset, dataset.markers, ...)`, applies any stored overrides, then calls `plotter.plot(plot_widget, dataset, result, t_start, t_end, **callbacks)`.
7. After plotting, `MainWindow.register_plots()` walks `plot_widget.scene().items()` and registers `PlotItem` instances with the `InteractivePlotWidget` for snap-to-trace marker placement.

### Manual Override Round-trip

1. User drags the Valsalva baseline region or a measurement dot, or right-click-deletes / double-click-inserts an RSA cycle.
2. The interactor (`BaselineRegionInteractor`, `CycleInteractor`) recomputes locally and invokes the `on_manual_override` / `on_point_override` / `on_cycle_override` callback wired by `AppController.plot_current_phase` (`autonomiclab/gui/app_controller.py:206-216`).
3. Callback updates `AppState.overrides[phase]`, sets `analysis_mode = "manual"`, calls `_save_overrides` → `override_store.save` (atomic via `.tmp` + `os.replace`, `autonomiclab/core/overrides.py:68`).
4. For point/cycle overrides, `plot_current_phase()` is invoked again so the analyzer reruns with the new overrides applied.

### .nsc Load Path

1. `AppController.load_nsc_file(nsc_path)` (`autonomiclab/gui/app_controller.py:114`) calls `DatasetService.load_nsc(nsc_path)` (`autonomiclab/core/dataset_service.py:88`).
2. `NscReader` opens the `.nsc` ZIP, parses `Measurement.xml`, then per requested channel reads paired uint32 X-ticks / uint16 Y-values from `<channel>.nsd` files (`autonomiclab/core/nsc_reader.py`).
3. Resulting `Dataset` has signals but no markers/regions (the format does not carry protocol annotations); the UI shows the Overview plot only.

### Export Path

1. User clicks **Export Excel** → `MainWindow._ctrl_export` → `AppController.export_current` (`autonomiclab/gui/app_controller.py:281`).
2. Looks up the active plotter via `PROTOCOL_REGISTRY[st.last_protocol_key]["plotter"]` and calls `plotter.export(plot_widget, last_result, results_dir, mode)`. The plotter delegates to `ExcelExporter` and `ImageExporter`.

### Login Flow

1. `__main__.main()` shows splash, then after `QTimer.singleShot(SPLASH_MS, launch)` runs `launch()` (`autonomiclab/__main__.py:94`).
2. `launch` builds `AppSettings`, optionally calls `sync_users_db(token, db_path)` (`autonomiclab/auth/sync.py:41`), instantiates `UserStore`, `GuestCounterStore`.
3. If `store.has_any_user()` is False → bypass login (first-run setup mode). Otherwise show `LoginDialog`; on Accept, `MainWindow` is shown.
4. `auth.session.login(user)` sets the module-level `_current_user` singleton consulted everywhere via `is_admin()` / `is_guest()`.

**State Management:**
- All mutable runtime state lives on `AppState` (one instance per `MainWindow`).
- All disk-persisted state: `<dataset>/overrides.json`, `<dataset>/results/*.xlsx`, `users.db` (synced), `guest_counter.json`, `~/.autonomiclab/settings.yaml`.

## Key Abstractions

**`Dataset`:**
- Purpose: One Finapres recording session — signals + markers + region windows + dataset path.
- Examples: `autonomiclab/core/models.py:60`.
- Pattern: Frozen-ish dataclass with helper methods (`get_signal`, `has_signal`, `phase_window`).

**`Signal`:**
- Purpose: A single time-series with name, times array, values array, unit.
- Examples: `autonomiclab/core/models.py:16`.
- Pattern: Dataclass with `__post_init__` length-mismatch repair, `slice(t_start, t_end)`, `__bool__` based on length.

**Protocol Registry / Strategy:**
- Purpose: Decouple phase routing from analysis/rendering implementations.
- Examples: `autonomiclab/plotting/registry.py:27-48`.
- Pattern: `dict[str, dict[str, Any]]` of analyzer+plotter instances, plus a keyword-list `_KEYWORDS` for fuzzy phase-name resolution. Adding a new protocol = add an `Analyzer` in `analysis/`, a `Plotter` in `plotting/`, and a registry entry.

**`WindowProtocol`:**
- Purpose: Structural type defining the subset of `MainWindow` methods `AppController` may call, breaking the cyclic import.
- Examples: `autonomiclab/gui/app_controller.py:40-54`.
- Pattern: `typing.Protocol`. `MainWindow` satisfies it implicitly via duck typing — no inheritance.

**Callback Protocols:**
- Purpose: Type-safe interactor → controller callbacks.
- Examples: `BaselineOverrideCallback`, `PointOverrideCallback`, `CycleOverrideCallback` in `autonomiclab/core/protocols.py:14-29`.
- Pattern: `typing.Protocol` with `__call__` signatures; consumed by plotters and bound to `AppController.on_*_override` lambdas.

**Result dataclasses (`ValsalvaResult`, `DeepBreathingResult`, `RSACycle`, `StandResult`):**
- Purpose: Carry analyzer outputs into plotters + Excel exporter without coupling to the analyzer's internal state.
- Examples: `autonomiclab/analysis/valsalva.py:22-62`, `autonomiclab/analysis/deep_breathing.py:19-51`.
- Pattern: `@dataclass` with `Optional[float]` fields and post-init defaults.

**Interactors (`BaselineRegionInteractor`, `CycleInteractor`):**
- Purpose: Encapsulate one interactive editing surface (its widgets, drag callbacks, recomputation).
- Examples: `autonomiclab/plotting/valsalva_baseline.py:28`, `autonomiclab/plotting/deep_breathing_cycles.py:26`.
- Pattern: Constructed by the plotter, owns its `LinearRegionItem`/dot ScatterPlotItems, calls back via `on_*_override` Protocols.

**`EscapeCloseMixin`:**
- Purpose: Esc-to-close + confirmation prompt for any window class.
- Examples: `autonomiclab/gui/close_mixin.py:9`. Used by `MainWindow` and `RawDataWindow`.

## Entry Points

**Application launch:**
- Location: `autonomiclab/__main__.py:53` (`main`).
- Triggers: `python -m autonomiclab`, `autonomiclab` console script (see `setup.py` `entry_points`), or PyInstaller `AutonomicLab.exe`.
- Responsibilities: Configure logger, install excepthook (suppresses stale-Qt-pointer `RuntimeError`s), find splash PNG, build `QApplication`, schedule `launch()` via `QTimer.singleShot`, run `app.exec()`.

**MainWindow standalone:**
- Location: `autonomiclab/gui/main_window.py:503` (`main`).
- Triggers: `python -m autonomiclab.gui.main_window` (developer convenience — bypasses login).
- Responsibilities: Build `QApplication` + `MainWindow` and `app.exec()`.

**Admin user creation:**
- Location: `scripts/create_admin.py`.
- Triggers: `python scripts/create_admin.py` from project root or alongside the installed `.exe`.
- Responsibilities: Interactive prompt → `UserStore.add_user(...)` to seed the first admin in `users.db`.

**Doc screenshot generator:**
- Location: `scripts/render_doc_screenshots.py`.
- Triggers: Manual run to regenerate `docs/figs/*.png`.

## Architectural Constraints

- **Threading:** Single-threaded Qt main loop. No `QThread` usage; no worker threads. All I/O (file load, openpyxl write, GitHub HTTP) runs on the GUI thread. Long operations briefly freeze the UI; `QApplication.processEvents()` is called manually in places (e.g., `AppController.export_current`, `autonomiclab/gui/app_controller.py:307`).
- **Global state:**
  - `auth.session._current_user` — module-level singleton holding the logged-in `User`.
  - `auth.crypto._FERNET` — module-level Fernet instance (key derived once at import).
  - `config.font_loader.FontLoader._config` and `_ui_zoom` — class-level singleton cache.
  - `utils.config.APP_NAME` / `APP_VERSION` — legacy constants, prefer `autonomiclab.__version__`.
- **Circular imports:**
  - `MainWindow` ↔ `AppController` would be circular; broken at runtime by `WindowProtocol` and `if TYPE_CHECKING:` import (`autonomiclab/gui/app_controller.py:23`).
  - Protocol callback types live in `core/protocols.py` (Qt-free) so plotters can import them without dragging GUI symbols into core.
- **Layer dependency direction:** `gui → plotting → analysis → core`. `gui → auth/config/export/utils`. Nothing in `core/` or `analysis/` imports Qt or pyqtgraph. Plotters import pyqtgraph but not GUI widgets directly (apart from interactor classes which use pyqtgraph items).
- **First-run bypass:** If `UserStore.has_any_user()` is False, login is skipped (`autonomiclab/__main__.py:114`). Run `scripts/create_admin.py` to seed.
- **PyInstaller / frozen detection:** `getattr(sys, "frozen", False)` and `sys._MEIPASS` are used in `__main__._log_path`, `__main__._find_splash_image`, and `config/app_settings._app_dir` to locate resources next to the `.exe`.
- **pyqtgraph stale C++ pointers:** `RuntimeError: ... has been deleted` is intentionally swallowed by the global excepthook (`autonomiclab/__main__.py:30`). Do not chase these as crashes.
- **Resize debounce:** Plot resize crashes are mitigated by a 50 ms `QTimer.singleShot` debounce; `processEvents()` and re-entrancy guards do not work here (per `CLAUDE.md`).

## Anti-Patterns

### Reaching into widget internals across layers

**What happens:** Earlier code paths (and a residual `_init_empty_plots` in `MainWindow`, `autonomiclab/gui/main_window.py:316`) directly create pyqtgraph `PlotItem`s on the View, bypassing the plotter classes.
**Why it's wrong:** Splits drawing logic between `MainWindow` and `plotting/`, breaks the View-passive contract, and makes per-protocol styling inconsistent.
**Do this instead:** Always go through `PROTOCOL_REGISTRY[key]["plotter"].plot(...)` or `OverviewPlotter.plot(...)`. The view should call `set_plot_stack_index(...)` and let `AppController.plot_current_phase` produce the scene.

### Importing GUI symbols into `core/` or `analysis/`

**What happens:** Tempting to add a `pg.QtCore` or `PyQt6` import in an analyzer for convenience.
**Why it's wrong:** Makes `core` and `analysis` un-testable headlessly and pulls Qt into PyInstaller bundles via paths that should stay pure-Python.
**Do this instead:** Define callback shapes as `typing.Protocol` in `autonomiclab/core/protocols.py` and let the GUI/plotting layer wire them up. Keep numpy/scipy as the only heavy dependencies of `analysis/`.

### Holding state on the View instead of `AppState`

**What happens:** Stashing `self._dataset` or `self._overrides` on `MainWindow`.
**Why it's wrong:** `AppController` mutates `AppState`; if `MainWindow` keeps its own copy, the two diverge.
**Do this instead:** Read everything from `self._state` (the shared `AppState` instance, `autonomiclab/gui/main_window.py:86`). Add new state by extending the `AppState` dataclass.

### Non-atomic writes to `overrides.json`

**What happens:** Direct `path.write_text(json.dumps(...))`.
**Why it's wrong:** A crash mid-write leaves a half-written file and loses the user's manual analysis.
**Do this instead:** Reuse `override_store.save` (`autonomiclab/core/overrides.py:68`) which writes to a sibling `.tmp` and uses `os.replace` for an atomic swap.

### Reading `users.db` or `guest_counter.json` directly

**What happens:** Hand-rolling SQLite or JSON reads in GUI code.
**Why it's wrong:** Bypasses Fernet decryption, schema validation, and HMAC verification.
**Do this instead:** Always go through `UserStore` (`autonomiclab/auth/user_store.py`) and `GuestCounterStore` (`autonomiclab/auth/guest_counter.py`).

## Error Handling

**Strategy:** Catch broad `Exception` at orchestration boundaries, log via `get_logger(__name__)`, surface a user-facing message through `WindowProtocol.set_status(...)` and the status bar; never let a single bad load take down the app.

**Patterns:**
- `AppController.load_dataset` and `load_nsc_file` wrap `DatasetService` calls in `try/except` and call `self._w.set_status("error", ...)` on failure (`autonomiclab/gui/app_controller.py:84`, `:114`).
- `AppController.plot_current_phase` wraps the analyse-and-plot block in `try/except` with `log.exception(...)` and a status-bar error message; the `finally` re-enables `plot.setUpdatesEnabled(True)` (`autonomiclab/gui/app_controller.py:230-235`).
- `core/finapres_loader.load_csv_signal` returns `None` on missing file; per-line `ValueError` is silently skipped — atomic `(t, v)` parse so blank-value rows do not desync arrays.
- `core/overrides.load` validates schema and returns `{}` on any failure with a `log.warning`, preventing `KeyError`s downstream.
- `auth/sync.sync_users_db` returns `False` on `URLError` (offline) and logs a warning; the local `users.db` is left untouched.
- `__main__._install_exception_hook` is a process-wide last-resort hook: stale-Qt-pointer `RuntimeError`s are downgraded to `WARNING`; everything else is `CRITICAL` plus the default tkinter-style traceback.

## Cross-Cutting Concerns

**Logging:**
- Single root logger configured in `autonomiclab/utils/logger.py` (`configure_root_logger`). Format: `"%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"`. Stream handler always; file handler when `log_file` is provided.
- Every module uses `log = get_logger(__name__)` at module top.
- Log file: `autonomiclab.log` next to the `.exe` (frozen) or in project root (dev).

**Validation:**
- Override schema validated on load (`autonomiclab/core/overrides.py:30`).
- `Signal.__post_init__` truncates mismatched `times`/`values` arrays with a warning (`autonomiclab/core/models.py:23`).
- HMAC verification on `guest_counter.json` (`autonomiclab/auth/guest_counter.py`) and Fernet decryption on `users.db` rows.

**Authentication:**
- Login required if any user exists; bypassed on first run.
- Admin-only menu guarded by `auth_session.is_admin()` (`autonomiclab/gui/main_window.py:297`).
- Guest path: 10 launches per machine, MAC-bound and HMAC-signed.
- `users.db` is encrypted SQLite synced via the GitHub Contents API.

**Configuration:**
- Two-layer: admin `config.yaml` (next to .exe) + per-user `~/.autonomiclab/settings.yaml`. Merged view via `AppSettings`.
- Fonts and layout percentages in `autonomiclab/config/fonts.yaml`.

---

*Architecture analysis: 2026-04-26*
