# External Integrations

**Analysis Date:** 2026-04-26

## APIs & External Services

**Source-control / sync:**
- GitHub Contents API — read and write the encrypted `users.db` to a private repo `John-H-Aal/autonomiclab-users`.
  - Client: `urllib.request` (stdlib, no SDK) in `autonomiclab/auth/sync.py`
  - Endpoint: `https://api.github.com/repos/John-H-Aal/autonomiclab-users/contents/users.db`
  - Auth: GitHub Personal Access Token, supplied via `config.yaml` key `users_db_token`; surfaced through `AppSettings.users_db_token` in `autonomiclab/config/app_settings.py`. The PAT is injected into `config.yaml` at install time by `installer.iss`, where the value comes from CI secret `USERS_DB_TOKEN` (`.github/workflows/release.yml`).
  - Operations: `sync_users_db()` (GET + replace local copy via temp-file rename), `push_users_db()` (PUT with current SHA).
  - Behaviour: silently skipped if the token is empty or the request fails (offline tolerant). Timeout: 10 s.

**Release downloads (informational):**
- GitHub Releases page opened from the in-app Help menu via `QDesktopServices.openUrl(QUrl("https://github.com/John-H-Aal/autonomiclab/releases/latest"))` (`autonomiclab/gui/main_window.py:293`). No API call; just a browser launch.

## Data Storage

**Databases:**
- Encrypted SQLite `users.db` — local file plus optional GitHub-backed sync.
  - Path: next to the `.exe` (or project root in dev), `AppSettings.users_db_path`.
  - Driver: `sqlite3` (stdlib).
  - Schema: single `users(username TEXT PK, role TEXT, is_active INTEGER, blob TEXT)` table; the `blob` column is a Fernet-encrypted JSON record holding the bcrypt password hash and profile fields. See `autonomiclab/auth/user_store.py` and `autonomiclab/auth/crypto.py`.
  - Encryption key: derived from a baked-in app secret with PBKDF2-HMAC-SHA256 (100k iterations) — defence-in-depth against casual editing, not a true secret.

**File Storage:**
- Local filesystem only. Datasets in the configured `data_folder` (default `~/Documents/AutonomicLab/data`); analysis exports to per-dataset Excel files; PNG plot exports next to the Excel file.

**Caching:**
- In-process only: `NscReader` in `autonomiclab/core/nsc_reader.py` caches decoded `Signal` objects and gap masks by channel. `FontLoader` in `autonomiclab/config/font_loader.py` caches the parsed `fonts.yaml`. No external cache.

## Authentication & Identity

**Auth Provider:**
- Custom, fully local. Implementation: `autonomiclab/auth/`.
  - `user_store.py` — bcrypt password hashing, Fernet-encrypted user records.
  - `session.py` — module-level singleton holding the current `User` (`login`, `logout`, `is_admin`, `is_guest`).
  - `models.py` — `Role` enum (`admin`, `investigator`, `guest`) and `User`/`GuestCounter` dataclasses.
  - `guest_counter.py` — MAC-bound, HMAC-SHA256-signed JSON counter (`guest_counter.json`) granting up to 10 launches per machine. MAC is hashed with `uuid.getnode()` + app secret in `crypto.mac_hash()`.
- First-run bypass: when `UserStore.has_any_user()` is `False`, login is skipped (`autonomiclab/__main__.py`). Initial admin is seeded via `scripts/create_admin.py`.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Rollbar/etc.). A custom `sys.excepthook` in `autonomiclab/__main__.py` logs unhandled exceptions and intentionally swallows pyqtgraph "wrapped C++ object deleted" `RuntimeError`s.

**Logs:**
- Python `logging` configured by `autonomiclab/utils/logger.py` (`configure_root_logger`). File: `autonomiclab.log` next to the `.exe`, or project root in dev. Module loggers obtained via `get_logger(__name__)`.

## CI/CD & Deployment

**Hosting:**
- Not a hosted app. End-user delivery is a Windows installer (`AutonomicLab_Setup_<version>.exe`) attached to a GitHub Release. Source: `https://github.com/John-H-Aal/autonomiclab`.

**CI Pipeline:**
- GitHub Actions, single workflow `.github/workflows/release.yml`, triggered on pushed tags `v*`.
  - `test` job — Ubuntu, Python 3.12, runs `pytest`.
  - `build` job — Windows, Python 3.12. Steps:
    1. Patch `autonomiclab/__init__.py` to set `__version__` from the tag.
    2. Install PyInstaller and Chocolatey-managed `upx`, `innosetup`, `pandoc`, `wkhtmltopdf`.
    3. Run PyInstaller (`--onefile --windowed`, hidden-imports `bcrypt` and `cryptography.*`, exclude unused PyQt6 modules and matplotlib/pandas/tkinter).
    4. Render `docs/user_guide.md` -> `dist/UserGuide.pdf` via `pandoc --pdf-engine=wkhtmltopdf --css user_guide.css`.
    5. Build `dist/AutonomicLab_Setup_<version>.exe` via `iscc installer.iss`, optionally setting installer password from secret `INSTALLER_PASSWORD` and embedding `USERS_DB_TOKEN`.
    6. Upload installer + versioned PDF to the release via `softprops/action-gh-release@v2`.

## Environment Configuration

**Required env vars:**
- None at runtime. All configuration is file-based.
- CI/release secrets (GitHub Actions, not env vars on the user machine):
  - `USERS_DB_TOKEN` — GitHub PAT with read/write access to `John-H-Aal/autonomiclab-users`. Embedded into the installer-generated `config.yaml`.
  - `INSTALLER_PASSWORD` — optional Inno Setup password protecting the installer.

**Secrets location:**
- `config.yaml` next to the installed `.exe` holds the GitHub PAT (`users_db_token`). On Windows installs this is `{localappdata}\AutonomicLab\config.yaml`, written by the installer's `[Code]` section in `installer.iss`.
- The current dev-tree `config.yaml` contains a real-looking `users_db_token` value. It is not read by this analyser, but anyone with read access to the working tree has access to that token.
- App-level Fernet secret + salt are baked into the binary at `autonomiclab/auth/crypto.py` (`_APP_SECRET`, `_SALT`).

## Webhooks & Callbacks

**Incoming:**
- None. The application does not run a server.

**Outgoing:**
- Outbound HTTPS to `api.github.com` (Contents API) for `users.db` GET/PUT.
- Outbound URL launch via the user's default browser to `https://github.com/John-H-Aal/autonomiclab/releases/latest` from the Help menu.

## File Format Integrations

**`.fef` / Finapres CSV — primary input format:**
- Loader: `autonomiclab/core/finapres_loader.py` (`load_csv_signal`, `detect_datetime_prefix`).
- Format: semicolon-separated CSV exported by Finapres NOVA, named `<DATETIME_PREFIX> <SIGNAL>.csv` (e.g. `2025-09-10_09.04.59 reBAP.csv`). Known signals include `reBAP`, `HR`, `Markers`. Header is 8 lines.
- Parsing rule: `(t, v)` columns must be parsed atomically — dropping blank-value rows independently desyncs the time and value arrays (documented sharp corner in `CLAUDE.md`).

**`.nsc` — Finapres NOVA binary format:**
- Reader: `autonomiclab/core/nsc_reader.py` (class `NscReader`).
- Container: ZIP archive (`zipfile` stdlib) containing per-channel `.nsd` files and `Measurement.xml` (parsed with `xml.etree.ElementTree`).
- Encoding (reverse-engineered, see module docstring): X = uint32 LE ticks at 50 µs/tick, Y = uint16 LE physical-value pairs scaled by `(MaxValue - MinValue) / 32768`. Pairs `(start, end)` per sample window; gaps are detected via a 10x expected-period window heuristic.
- Preferred over CSV for NOVA data per `CLAUDE.md`.

**Markers / overrides:**
- `autonomiclab/core/markers_handler.py`, `autonomiclab/core/overrides.py` — protocol-marker post-processing (per-dataset adjustments).

## Plotting Integration

- pyqtgraph is the canonical plot stack. All plot widgets are `PlotItem`/`GraphicsLayoutWidget`-based and live under `autonomiclab/plotting/`:
  - `overview.py`, `valsalva.py`, `valsalva_baseline.py`, `deep_breathing.py`, `deep_breathing_cycles.py`, `stand.py`, `helpers.py`.
  - `registry.py` maps a `Protocol` value to its plot class.
- pyqtgraph image export uses `pyqtgraph.exporters.ImageExporter` in `autonomiclab/export/image.py` (PNG only).
- Known runtime quirks (from `CLAUDE.md`): stale-C++-object `RuntimeError`s are suppressed in the global excepthook; resize-induced `ViewBox` crashes are mitigated with a 50 ms `QTimer.singleShot` debounce.

## Export Integrations

**Excel (`autonomiclab/export/excel.py`):**
- openpyxl writes Valsalva and Deep Breathing result workbooks (`<dataset>_<protocol>_results_<timestamp>_<mode>.xlsx`) with custom fonts/borders/section fills.
- Pillow (`PIL.Image`) is used to read PNG dimensions before embedding plots into the workbook via `openpyxl.drawing.image.Image` (scaled to 80%).

**Image (`autonomiclab/export/image.py`):**
- pyqtgraph's `ImageExporter` exports a full scene (`GraphicsLayoutWidget.scene()`), individual `PlotItem`s, or a temporarily zoomed scene to PNG.

**PDF (release-time only):**
- `pandoc` + `wkhtmltopdf` render `docs/user_guide.md` to `dist/UserGuide.pdf` during the GitHub Actions build. The PDF is shipped by the Inno Setup installer to the install directory and to the desktop as a shortcut. weasyprint is declared as a dependency but not currently imported by the runtime code.

---

*Integration audit: 2026-04-26*
