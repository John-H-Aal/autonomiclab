# Codebase Concerns

**Analysis Date:** 2026-04-26

## Tech Debt

**Stand Test analysis is a stub:**
- Issue: `StandResult` is empty (just `pass`); `StandAnalyzer.analyze` does no signal processing and returns an empty placeholder.
- Files: `autonomiclab/analysis/stand.py:13-22`
- Impact: Selecting a "Stand" phase produces no measurements, no export rows, and no plot annotations. The Stand protocol is registered in `autonomiclab/plotting/registry.py` but yields nothing usable.
- Fix approach: Implement orthostatic SBP/DBP drop detection and HR response (30:15 ratio) following the same Result-dataclass + Analyzer pattern used in `analysis/valsalva.py` and `analysis/deep_breathing.py`.

**Doc/code drift — "Dropbox sync" is actually GitHub Contents API:**
- Issue: `CLAUDE.md` and the auth memory note describe `users.db` sync as "Dropbox" / "OneDrive", but the implementation talks to the GitHub REST API on the private `John-H-Aal/autonomiclab-users` repo.
- Files: `autonomiclab/auth/sync.py:17-19`, `CLAUDE.md` ("auth system" section), memory `project_auth.md`
- Impact: Confusing for future maintainers; the credential type, failure modes, and rate limits are completely different.
- Fix approach: Update `CLAUDE.md` and the auth memory note to say "GitHub Contents API". Single search-and-replace.

**Module-level singletons block multi-window/multi-user reasoning:**
- Issue: Auth session is a module global (`_current_user`); Fernet cipher is constructed once at import time from a baked-in secret.
- Files: `autonomiclab/auth/session.py:7`, `autonomiclab/auth/crypto.py:32`
- Impact: Unit tests cannot run in parallel without leaking auth state across tests; only one user identity is representable per process.
- Fix approach: Acceptable for a single-window desktop app — note in design docs but do not refactor unless multi-tenant becomes a requirement.

**Stray attributes attached to pyqtgraph scene:**
- Issue: `_db_click_handler` and `_db_menu` are stuffed onto `plot.scene()` as ad-hoc attributes to dodge GC and stale signal connections.
- Files: `autonomiclab/plotting/deep_breathing_cycles.py:64,72,173`
- Impact: Brittle — changing pyqtgraph internals could break this; values silently leak across plot rebuilds.
- Fix approach: Track the menu and handler on the `RSACycleEditor` instance (or whatever class wraps the deep-breathing plot) and disconnect explicitly in a teardown method.

**Direct monkey-patch of `scene().mousePressEvent`:**
- Issue: `InteractivePlotWidget.__init__` rebinds the scene's `mousePressEvent` to its own method and stashes the original on `self`.
- Files: `autonomiclab/gui/widgets/interactive_plot.py:25-27`
- Impact: Bypasses pyqtgraph's normal event filter chain; if pyqtgraph adds its own pre-handler later it will be silently overwritten.
- Fix approach: Use `scene().sigMouseClicked` (already used in `deep_breathing_cycles.py:71`) with `ev.button()` filtering instead of replacing the method.

**No log rotation — `autonomiclab.log` grows unbounded:**
- Issue: `configure_root_logger` adds a plain `logging.FileHandler` with no size cap or rotation policy and the logger runs at `DEBUG`.
- Files: `autonomiclab/utils/logger.py:24-42`
- Impact: On a long-running install the log eventually fills disk; on Windows next to the .exe this can also be in a write-protected `Program Files` location.
- Fix approach: Switch to `logging.handlers.RotatingFileHandler(maxBytes=5*1024*1024, backupCount=3)`. Two-line change.

## Known Bugs

**pyqtgraph stale C++ object errors swallowed in global excepthook:**
- Symptoms: `RuntimeError: wrapped C++ object of type X has been deleted` is logged at WARNING and silently dropped.
- Files: `autonomiclab/__main__.py:28-34`
- Trigger: pyqtgraph still emits signals (or paints) into `ViewBox`/`AxisItem`/`InfiniteLine` C++ objects that Qt has already destroyed during a plot rebuild or window close.
- Workaround: The hook swallows the exception so the process keeps running. Documented in `CLAUDE.md` ("known sharp corners") as expected behaviour. The real fix is correct widget lifetime management in plot code, not a deeper hook.

**Resize-storm crash mitigation — only present in RawDataWindow:**
- Symptoms: Without debounce, fast resize / checkbox toggling crashed pyqtgraph during paint while widgets were being moved between layouts.
- Files: `autonomiclab/gui/raw_data_window.py:141-146,344-365` (50 ms `QTimer` debounce + `setUpdatesEnabled(False)` + `_rebuilding` re-entrancy guard + `sip.isdeleted(self)` check)
- Trigger: Multiple `_rebuild` invocations within ~50 ms (rapid checkbox clicks, window resize while a rebuild is in flight).
- Workaround in code: 50 ms single-shot timer that restarts on overlap, paint suppression around `_rebuild_inner`, plus an explicit `_rebuilding` flag because re-entrancy guards alone and `processEvents()` were proven not to work.
- Concern: `MainWindow` and `InteractivePlotWidget` do **not** use the same pattern — they call `setUpdatesEnabled(False)` around `plot_current_phase` (`gui/app_controller.py:160-235`) but have no resize debounce. If the same crash class reappears in the main plot under fast resize, the fix template lives in `raw_data_window.py`.

**Finapres loader: blank-value rows would desync arrays if dropped independently:**
- Symptoms: A blank value column would historically produce times array longer than values array, leading to indexing errors deep in analysis.
- Files: `autonomiclab/core/finapres_loader.py:62-70`
- Current code: `t = float(parts[0])` and `v = float(parts[1])` are inside the same `try`, and the `(t, v)` pair is only appended if both succeed. A blank value raises `ValueError` and the entire row is skipped.
- Trigger: Finapres CSV exports occasionally have rows with the time column populated but the value column empty (e.g. during sensor dropout).
- Watch list: any future refactor that splits the parse into `try float(t); times.append(t); try float(v); values.append(v)` would re-introduce the desync bug. Comment on line 66 (`# raises ValueError if blank`) preserves the invariant — keep it.

**No headless GUI test — UI regressions only catch when running the app:**
- Symptoms: Resize / ViewBox crashes, plot lifecycle bugs, and admin-panel flows can only be exercised manually.
- Files: `tests/conftest.py` (no Qt fixture); `pytest.ini` is bare (`testpaths = tests`).
- Existing tests cover: `test_dataset_service.py`, `test_finapres_loader.py`, `test_guest_counter.py`, `test_nsc_reader.py`, `test_user_store.py` — all pure-Python, no `QApplication`.
- Workaround: `pytest-qt` + `QT_QPA_PLATFORM=offscreen` would let CI exercise the widgets, but no setup exists today. CLAUDE.md explicitly flags this.

**`autonomiclab/auth/__init__.py` is empty (1 line):**
- Symptoms: The `auth` package re-exports nothing, so every consumer must import from full paths (`autonomiclab.auth.session`, `autonomiclab.auth.user_store`).
- Files: `autonomiclab/auth/__init__.py`
- Impact: Cosmetic — but mismatched with how `auth_session` is aliased on import in `gui/main_window.py:22`. Low priority.

## Security Considerations

**GitHub Personal Access Token committed to working tree (not git, but on disk):**
- Risk: `config.yaml` in the working tree contains a live `github_pat_…` token granting read/write to the private `autonomiclab-users` repo (which holds the encrypted user database for every install).
- Files: `config.yaml:10` (gitignored — `.gitignore:23`)
- Current mitigation: `.gitignore` excludes `config.yaml`, `users.db`, and `guest_counter.json`; `git log --diff-filter=A -- config.yaml` shows it has never been committed.
- Recommendations: Rotate the token immediately if this checkout has ever been shared, archived, or copied to another machine. Move the token out of a YAML file checked-in alongside an installer template — at minimum keep the dev copy outside the repo (e.g. `~/.autonomiclab/config.yaml`) and load via `_USER_SETTINGS_FILE` first. Long-term: the GitHub-PAT-bundled-in-installer model means every user with the .exe has a R/W token to your users repo. Consider a minimal authenticated proxy or per-machine deploy keys.

**Encryption key derived from a hardcoded app secret:**
- Risk: `_APP_SECRET = b"AutonomicLab-2026-GAT-secret-xK9mP2"` is the entire entropy source for both Fernet user-record encryption and HMAC of the guest counter. Anyone with the binary or source can decrypt every `users.db` and forge guest counters.
- Files: `autonomiclab/auth/crypto.py:17-29,50-54`
- Current mitigation: Doc comment ("defence-in-depth so casual users cannot simply read/edit the database with a text editor") accurately states the threat model.
- Recommendations: Acceptable for the stated threat model (Astrid's clinic, not adversarial). If users.db ever needs to leave the trusted machine boundary, replace with an admin-supplied passphrase or per-install random key stored in OS keychain.

**First-run bypass: empty `users.db` skips authentication entirely:**
- Risk: If `users.db` is missing, corrupted into "no users", or the file is renamed away, the app starts with no login dialog and `auth_session.is_admin()` returns `False` — but the rest of the app runs normally.
- Files: `autonomiclab/__main__.py:113-115`, `autonomiclab/auth/user_store.py:145-148`
- Current mitigation: The admin menu in `MainWindow._init_menu_bar` (`gui/main_window.py:297`) is gated on `auth_session.is_admin()`, which is False in bypass mode → admin features hidden.
- Recommendations: Document that anyone able to delete `users.db` from the install folder gets a passwordless app. On Windows installs to `Program Files`, that requires admin rights to do; on `%LOCALAPPDATA%` installs, it does not. Consider a "first run flag" file that `create_admin.py` removes, so the bypass is genuinely one-shot.

**Guest counter is MAC-bound but trivially bypassed:**
- Risk: HMAC key is derived from the same `_APP_SECRET`, so anyone with the binary can mint a valid signed counter file. Deleting `guest_counter.json` also resets it (next launch creates a fresh 10-launch counter).
- Files: `autonomiclab/auth/guest_counter.py:30-90`, `autonomiclab/auth/crypto.py:50-59`
- Current mitigation: Stops casual editing in a text editor; deletion is detected as "first launch on this machine" and re-issued.
- Recommendations: Match the threat model — this is a soft license meter, not anti-piracy. Documented behaviour is fine; do not over-engineer.

**Lost-update race on `users.db` GitHub sync:**
- Risk: Two admins on different machines edit `users.db` near-simultaneously. Both call `push_users_db` → both call `_get_remote` to read `current_sha` → both PUT with that SHA. The second PUT's `sha` is now stale; GitHub returns 409 — but `push_users_db` only catches `URLError`, so a 409 propagates as a generic `Exception` and is logged but not surfaced; alternately, with sufficient timing slop, the second push could replace the first if the first hasn't finalized its SHA yet.
- Files: `autonomiclab/auth/sync.py:72-109`, `autonomiclab/gui/auth/admin_panel.py:115-128`
- Current mitigation: User-visible warning ("Could not sync the user list to GitHub. Changes are saved locally.") on `push_users_db` returning False.
- Recommendations: On 409, `_get_remote` again, replay the PUT with the new SHA after warning the admin that someone else edited. Or detect divergence by hashing the local pre-edit copy vs current remote. Document that simultaneous admin edits are unsupported.

## Performance Bottlenecks

**`finapres_loader.load_csv_signal` line-by-line Python parsing:**
- Problem: Per-line `split(';')` + `float()` + `list.append` for every sample of every CSV. ECG channels can run 100+ MB.
- Files: `autonomiclab/core/finapres_loader.py:43-78`
- Cause: `f.readlines()[skip_header:]` materializes the whole file into a list, then iterates again.
- Improvement path: `numpy.genfromtxt(csv_file, delimiter=';', skip_header=8, missing_values='', filling_values=np.nan, usecols=(0,1))` — orders of magnitude faster — then drop NaN rows pairwise. The atomic-pair invariant (CLAUDE.md) is preserved because the drop happens on the same row index.

**`_get_remote` is called twice for every push:**
- Problem: `push_users_db` calls `_get_remote` purely to fetch `current_sha`, downloading the entire users.db payload over the network just to get a 40-character hash.
- Files: `autonomiclab/auth/sync.py:80-85`
- Cause: GitHub Contents API returns content + sha as one payload; there is a `?ref=` HEAD-only path but the helper does not use it.
- Improvement path: A `HEAD` against the same URL returns the SHA in headers (`Etag`-ish); or use the trees API. Low priority since `users.db` is small.

**`overrides.json` rewritten on every drag-release:**
- Problem: Each marker drag triggers `_save_overrides` → full JSON rewrite of all overrides for the dataset.
- Files: `autonomiclab/gui/app_controller.py:255-261, 320-323`, `autonomiclab/core/overrides.py:68-87`
- Cause: Save-on-every-mutation pattern; no debounce.
- Improvement path: Debounce save to ~500 ms after last edit using a `QTimer`. File is small (KB) so this is mostly disk-wear concern, not latency.

**`InteractivePlotWidget._snap_to_trace` is O(plots × curves × samples):**
- Problem: Right-click marker placement scans every curve in every plot, calling `np.argmin(np.abs(x_data - view_pos.x()))` per curve.
- Files: `autonomiclab/gui/widgets/interactive_plot.py:45-109`
- Cause: Linear search per click.
- Improvement path: For sorted time arrays (which Finapres always provides), `np.searchsorted` is O(log n). Single click feels fine today, so low priority.

## Fragile Areas

**`InteractivePlotWidget.clear()` — manual cleanup of `InfiniteLine` markers:**
- Files: `autonomiclab/gui/widgets/interactive_plot.py:121-142`
- Why fragile: pyqtgraph's `GraphicsLayoutWidget.clear()` deletes ViewBoxes but leaves standalone scene items with stale parent refs; the override removes tracked markers from the scene before delegating. Any new code path that adds standalone scene items (e.g. text overlays, legends) and does not register them in `marker_lines` will recreate the original crash.
- Safe modification: New scene-attached items must be tracked in a dict on `InteractivePlotWidget` and removed inside `clear()` before `super().clear()`.
- Test coverage: Zero — no headless Qt tests exist.

**`RawDataWindow._do_rebuild` — multi-flag re-entrancy:**
- Files: `autonomiclab/gui/raw_data_window.py:347-365`
- Why fragile: Three independent guards (`sip.isdeleted(self)`, `_rebuilding` flag, 50 ms `QTimer`, `setUpdatesEnabled(False)`). Removing any one has historically caused crashes.
- Safe modification: Treat the four guards as a single atomic unit. Document at top of method that "all four are load-bearing — see git log for crash history".
- Test coverage: None — manual repro only.

**Finapres `(t, v)` atomic-pair parsing:**
- Files: `autonomiclab/core/finapres_loader.py:62-70`
- Why fragile: Future "optimization" splitting the parse into separate try blocks would silently desync arrays — breaks all downstream signal alignment. The single comment `# raises ValueError if blank` on line 66 is the only in-code reminder.
- Safe modification: Keep `t` and `v` parses in the same `try`. If migrating to `np.genfromtxt`, validate `len(times) == len(values)` post-load.
- Test coverage: `tests/test_finapres_loader.py` exercises real data but does not have a synthetic blank-value-row regression test. Add one.

**NscReader holds an open ZipFile until `close()`:**
- Files: `autonomiclab/core/nsc_reader.py:69,135-142`
- Why fragile: `__init__` opens `zipfile.ZipFile`; only `close()` / context-manager exit releases it. `DatasetService.load_nsc` uses `with NscReader(...) as reader:` correctly (`core/dataset_service.py:98`), but any new caller that forgets the `with` statement leaks a file handle until GC.
- Safe modification: Always use `with NscReader(...)` or call `.close()` explicitly. Consider adding `__del__` to close on GC as a backstop.
- Test coverage: `tests/test_nsc_reader.py` exists and uses real data when available.

**`_PROTOCOL_SLUG` mapping diverges from `PROTOCOL_REGISTRY` keys:**
- Files: `autonomiclab/gui/app_controller.py:33-37`, `autonomiclab/plotting/registry.py`
- Why fragile: `_PROTOCOL_SLUG` and the registry both key on protocol strings (`"valsalva"`, `"deep breath"`, `"stand"`). Adding a fourth protocol requires touching both maps and `analysis/` and `plotting/`.
- Safe modification: Single dataclass per protocol exposing `key`, `slug`, `analyzer`, `plotter`.
- Test coverage: Indirectly via `tests/test_dataset_service.py`.

## Scaling Limits

**Single-process desktop app, single user per process:**
- Current capacity: One QMainWindow, one logged-in user via module-level `_current_user`, one open dataset at a time (`AppState`).
- Limit: Cannot run two analyses in parallel; cannot compare two datasets side by side without launching two processes.
- Scaling path: Out of scope — this is a desktop tool by design.

**`users.db` size in GitHub Contents API:**
- Current capacity: Tens of users, file is ~few KB.
- Limit: GitHub Contents API caps single-file PUT at ~100 MB; encrypted-blob-per-user means 1 KB/user → ~100k users theoretical.
- Scaling path: Not a real concern; clinic-scale.

**`autonomiclab.log` unbounded growth:**
- Current capacity: Bounded only by disk.
- Limit: Long-running installs eventually fill disk.
- Scaling path: Switch to `RotatingFileHandler` (see Tech Debt above).

## Dependencies at Risk

**`weasyprint>=60.0` for PDF/image export:**
- Risk: WeasyPrint depends on Pango/Cairo system libraries on Linux/macOS and bundles GTK on Windows. PyInstaller bundling on Windows has historical pain points (missing DLLs, font fallback differences).
- Files: `requirements.txt:8`, `autonomiclab/export/image.py`
- Impact: Build breakage on a PyInstaller release if WeasyPrint's bundle path changes.
- Migration plan: For PDF/image export, `Pillow` alone or `reportlab` would remove the GTK/Cairo dependency. Reserve WeasyPrint for HTML→PDF if that path is actually used.

**`pyqtgraph` C++/Python lifetime races:**
- Risk: The "stale C++ object" pattern is a known pyqtgraph behaviour; updates can change which paths trigger it.
- Files: imported across `autonomiclab/plotting/*.py` and `autonomiclab/gui/widgets/interactive_plot.py`
- Impact: Major-version pyqtgraph upgrade would require revalidating every `clear()`, `setUpdatesEnabled`, and resize path manually (no automated test).
- Migration plan: Pin to a known-good version in `requirements.txt` (currently `>=0.13.0` is too loose — bump to `>=0.13.0,<0.14`).

**`PyQt6>=6.4.0` — broad version range:**
- Risk: PyQt6 6.5+ changed several enum import paths (`Qt.AlignmentFlag` etc.) — already used correctly, but a 6.7+ jump may bring more breaks.
- Files: `requirements.txt:1`
- Impact: Silent UI regressions when bumping PyQt6.
- Migration plan: Pin to `<6.8` in `requirements.txt` until tested.

## Missing Critical Features

**Stand Test analysis (see Tech Debt):**
- Problem: Empty stub.
- Blocks: One of three stated GAT protocols cannot be analyzed or exported.

**No automated test for the `PhysioCalActive` calibration-guard suppression logic in Valsalva:**
- Problem: `valsalva.py:155-187` invalidates Phase III/IV results if calibration was active. No test asserts this behaviour.
- Blocks: A future refactor of `_cal_active` could silently re-enable contaminated PRT/overshoot values.

**No headless test of override save/load round-trip with a real Qt event loop:**
- Problem: `core/overrides.py` has unit-testable logic but `app_controller.on_*_override` callbacks are only invoked via a running `QApplication`.
- Blocks: Override-callback regressions only caught manually.

## Test Coverage Gaps

**All GUI code (`gui/`, `plotting/`):**
- What's not tested: `MainWindow`, `AppController`, `RawDataWindow`, `InteractivePlotWidget`, every plotter, the admin panel, the login dialog.
- Files: `autonomiclab/gui/**`, `autonomiclab/plotting/**`
- Risk: All resize/lifetime crashes, override-callback bugs, and admin-flow regressions are caught only by manual repro.
- Priority: Medium — set up `pytest-qt` with `QT_QPA_PLATFORM=offscreen` so smoke tests at least construct the windows.

**Auth sync (`auth/sync.py`):**
- What's not tested: GitHub fetch, push, lost-update race, offline behaviour, malformed token. The tests directory has `test_user_store.py` and `test_guest_counter.py` but no `test_sync.py`.
- Files: `autonomiclab/auth/sync.py`
- Risk: A bad GitHub API response (rate limit, 409, 404 on first-ever push) could deadlock the admin flow.
- Priority: Medium — mock `urlopen` and assert the failure paths.

**Excel export (`export/excel.py`):**
- What's not tested: Workbook structure, formula cells, image embedding (`_embed_images`), no-result handling.
- Files: `autonomiclab/export/excel.py`
- Risk: Layout regressions only caught when Astrid opens the file.
- Priority: Low — assert presence of named ranges / cell values via `openpyxl.load_workbook`.

**Calibration-guard suppression in Valsalva analysis:**
- What's not tested: `_cal_active` triggering on Baseline / Phase III+IV and the resulting field-suppression cascade.
- Files: `autonomiclab/analysis/valsalva.py:155-187`
- Risk: Silently restoring contaminated PRT/VR/BRSa to exported results.
- Priority: High — this guard exists because clinical conclusions depend on it.

**`overrides.py` schema validation:**
- What's not tested: `_validate` rejection paths.
- Files: `autonomiclab/core/overrides.py:30-46`
- Risk: A subtle regression that lets an invalid override through would crash deep inside an analyzer.
- Priority: Medium — pure-Python, easy to test.

**`finapres_loader` blank-value-row regression:**
- What's not tested: Synthetic CSV with rows missing the value column.
- Files: `autonomiclab/core/finapres_loader.py`
- Risk: Future refactor re-introduces the array-desync bug.
- Priority: High — write the test.

**No TODO/FIXME/HACK/XXX markers found in source.**
- The codebase is unusually clean of breadcrumb comments — concerns above were inferred from architecture and behaviour, not from `# TODO` notes.

---

*Concerns audit: 2026-04-26*
