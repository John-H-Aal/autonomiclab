# AutonomicLab

PyQt6 desktop app for GAT (autonomic nervous system) protocol analysis. Author: Astrid Juhl Terkelsen. Dev/maintained by John Hansen on Linux; deployed to Windows via PyInstaller.

## Run (dev)
```bash
source venv/bin/activate
python -m autonomiclab
```
Log: `autonomiclab.log` in project root.

## Module map
| Path | Responsibility |
|---|---|
| `core/` | Data loading (`finapres_loader`, `nsc_reader`, `dataset_service`), domain models, protocol definitions |
| `analysis/` | Signal-processing algorithms per protocol (valsalva, deep_breathing, stand) |
| `plotting/` | pyqtgraph plot classes per protocol; `registry.py` maps protocol → plot |
| `gui/` | `main_window`, `app_controller`, `app_state`, `raw_data_window`, widgets |
| `auth/` | `user_store` (encrypted SQLite), `session`, `guest_counter`, `sync` (GitHub Contents API), `crypto` |
| `export/` | Excel (openpyxl) and image (Pillow/WeasyPrint) export |
| `config/` | `AppSettings` (config.yaml wrapper), font loader |

## Data formats
- **`.fef`** — primary Finapres CSV export; loaded by `finapres_loader.py`. Parse `(t, v)` columns as atomic pairs — blank-value rows cause array desync if dropped independently.
- **`.nsc`** — Finapres NOVA binary format (ZIP of `.nsd` files); loaded by `NscReader` in `nsc_reader.py`. Full format spec is in the file. Prefer this over CSV for NOVA data.

## Auth system
- Three roles: admin, investigator, guest (10-launch MAC-bound counter).
- `users.db` = encrypted SQLite (Fernet-encrypted records, bcrypt password hashes). On launch, `autonomiclab/auth/sync.py:sync_users_db()` GETs `users.db` from the private GitHub repo `John-H-Aal/autonomiclab-users` via the Contents API and replaces the local copy if it differs. Offline-tolerant: silent skip on failure.
- Two PATs are used:
  - `users_db_token` — read-only (Contents: read); shipped in every installer via CI secret `USERS_DB_READ_TOKEN`; used only by `sync_users_db()` on launch.
  - `users_db_admin_token` — write-capable; NOT shipped; admin adds manually to `config.yaml` on their machine. Used only by `push_users_db()` when Admin Panel closes. If absent, Admin Panel close shows a "Sync not configured" warning instead of pushing.
- **First-run bypass**: if `users.db` has no users, the login dialog is skipped. Seed the first admin via `scripts/create_admin.py`.
- Admin menu in `MainWindow` visible only when `auth_session.is_admin()`.

## Known sharp corners
- **pyqtgraph stale C++ objects**: `RuntimeError: wrapped C++ object deleted` is swallowed in the global excepthook — not a real crash, don't chase it.
- **Plot resize/ViewBox crashes**: fix is a 50 ms `QTimer.singleShot` debounce on resize. Re-entrancy guards and `processEvents()` do not work here.
- **UI cannot be tested without running the app** — no headless Qt test setup exists.

## Build / release
Push a version tag → GitHub Actions builds the Windows `.exe` (~3–5 min):
```bash
git tag v1.x.x && git push origin v1.x.x
```
Release artifacts: `AutonomicLab_Setup_<version>.exe`, `UserGuide-<version>.pdf`. See `BUILDING.md`. (Config and splash are bundled into the installer, not standalone release files.)

## Style
- Responses must be as short as possible. No filler, no preamble, no "here's what I did" recaps.
- Don't explain what you're about to do — just do it.
- No comments in code unless the WHY is non-obvious.
- Diagnose root cause before proposing a fix.
