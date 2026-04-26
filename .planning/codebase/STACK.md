# Technology Stack

**Analysis Date:** 2026-04-26

## Languages

**Primary:**
- Python >=3.9 (CI builds on 3.12) — all application code under `autonomiclab/`

**Secondary:**
- PowerShell — local Windows build script `build.ps1`
- Inno Setup script — Windows installer definition `installer.iss`
- YAML — `config.yaml`, `autonomiclab/config/fonts.yaml`, GitHub Actions workflow
- Markdown — `docs/user_guide.md` (user guide source compiled to PDF)
- CSS — `docs/user_guide.css` (PDF stylesheet for pandoc/wkhtmltopdf)

## Runtime

**Environment:**
- Python interpreter (`>=3.9` declared in `setup.py`; CI/release uses Python 3.12 per `.github/workflows/release.yml`)
- Distributed to end users as a frozen PyInstaller `.exe` (Windows). On Linux, run via the project venv (`source venv/bin/activate; python -m autonomiclab`).

**Package Manager:**
- pip
- Lockfile: missing — only `requirements.txt` (loose pins, e.g. `PyQt6>=6.4.0`) and `requirements-dev.txt`

## Frameworks

**Core:**
- PyQt6 >=6.4.0 — desktop GUI framework. Entry point: `autonomiclab/__main__.py` instantiates `QApplication` and `MainWindow`. Used throughout `autonomiclab/gui/`.
- pyqtgraph >=0.13.0 — plotting layer (uses Qt under the hood). All plot classes live in `autonomiclab/plotting/` and `autonomiclab/plotting/registry.py` maps protocols to plot widgets.

**Testing:**
- pytest >=8.0 — test runner. Config: `pytest.ini` (`testpaths = tests`, `-v --tb=short`). Tests live in `tests/` (`test_dataset_service.py`, `test_finapres_loader.py`, `test_guest_counter.py`, `test_nsc_reader.py`, `test_user_store.py`).

**Build/Dev:**
- PyInstaller — packages the app into a single Windows `.exe`. Invocation in `build.ps1` and `.github/workflows/release.yml` (`--onefile --windowed --name AutonomicLab`).
- UPX — exe compression, installed via Chocolatey in CI (`choco install upx`).
- Inno Setup (`iscc`) — produces the Windows installer `AutonomicLab_Setup_<version>.exe` from `installer.iss`.
- pandoc + wkhtmltopdf — render `docs/user_guide.md` -> `dist/UserGuide.pdf` during release (CI step in `.github/workflows/release.yml`). Both installed via Chocolatey.

## Key Dependencies

**Critical:**
- numpy >=1.24.0 — array math across `autonomiclab/core/`, `autonomiclab/analysis/`, `autonomiclab/plotting/`. Used in `finapres_loader.py`, `nsc_reader.py`, signal-processing modules.
- scipy >=1.10.0 — peak detection. Imported in `autonomiclab/analysis/deep_breathing.py` (`from scipy.signal import find_peaks`).
- PyYAML >=6.0 — config and font definition parsing. Used by `autonomiclab/config/app_settings.py` and `autonomiclab/config/font_loader.py`.
- bcrypt >=4.0.0 — password hashing in `autonomiclab/auth/user_store.py`. Listed as PyInstaller `--hidden-import`.
- cryptography >=42.0.0 — Fernet encryption + PBKDF2 key derivation in `autonomiclab/auth/crypto.py`. Listed as PyInstaller `--hidden-import` along with `cryptography.hazmat.primitives.kdf.pbkdf2` and `cryptography.hazmat.backends.openssl`.

**Infrastructure:**
- openpyxl >=3.1.0 — Excel result export in `autonomiclab/export/excel.py` (styles, drawing, image embedding).
- Pillow >=9.0.0 — image dimension probing for embedded plot PNGs in `autonomiclab/export/excel.py` (`from PIL import Image as PILImage`).
- weasyprint >=60.0 — declared in `requirements.txt`. Not currently imported anywhere in the source tree (no `weasyprint` references found under `autonomiclab/` or `scripts/`); PDF rendering at release time is performed by pandoc + wkhtmltopdf in CI, not by weasyprint at runtime.
- Standard-library modules used as infra: `sqlite3` (encrypted user DB), `urllib.request` (GitHub API client), `zipfile` + `xml.etree.ElementTree` (`.nsc` parsing), `hashlib`/`hmac`/`uuid` (MAC-bound guest counter signing).

## Configuration

**Environment:**
- Two-layer config (see `autonomiclab/config/app_settings.py`):
  - `config.yaml` — admin/deployment file, lives next to the `.exe` (or project root in dev). Keys: `data_folder`, `users_db_token` (GitHub PAT for `users.db` sync), `allow_guest`, `allowed_users`.
  - `~/.autonomiclab/settings.yaml` — per-user prefs (`data_folder` override, `ui_zoom`).
- Font config: `autonomiclab/config/fonts.yaml` (bundled into the PyInstaller exe via `--add-data`).
- No `.env` files in use; secrets (GitHub PAT for `users.db`, installer password) are injected at build time via GitHub Actions secrets `INSTALLER_PASSWORD` and `USERS_DB_TOKEN`.

**Build:**
- `setup.py` — setuptools metadata (name, version 0.1.0, install_requires, console-script entry point `autonomiclab=autonomiclab.__main__:main`). Note: runtime version is sourced from `autonomiclab/__init__.py` (`__version__ = "1.0.31"`), which CI rewrites from the pushed git tag.
- `requirements.txt`, `requirements-dev.txt` — pip dependency pins.
- `build.ps1` — local Windows PyInstaller invocation.
- `installer.iss` — Inno Setup definition, includes `[Code]` section that writes a deployment-time `config.yaml` with the user's data folder and the embedded `users_db_token`.
- `.github/workflows/release.yml` — CI/release pipeline (test on Ubuntu, build/installer on Windows).

## Platform Requirements

**Development:**
- Linux (current dev/maintenance host) or Windows. Python venv in `venv/`.
- `python -m autonomiclab` to launch (see `CLAUDE.md`). Log file: `autonomiclab.log` in project root.
- A live Qt display is required — there is no headless test setup for the GUI.

**Production:**
- Windows 11 desktop. Distributed as `AutonomicLab_Setup_<version>.exe` (Inno Setup installer) producing:
  - `AutonomicLab.exe` (PyInstaller single-file, windowed)
  - `config.yaml` (auto-written by the installer)
  - `autonomiclab_splash.png`
  - `UserGuide.pdf`
- Install location: `{localappdata}\AutonomicLab` (per-user, `PrivilegesRequired=lowest` in `installer.iss`).
- Data folder created at `{userdocs}\AutonomicLab\data`.

---

*Stack analysis: 2026-04-26*
