# AutonomicLab — Requirements Specification

**Derived by reverse requirements engineering from the implemented codebase.**
*Version: 1.1.0 (derived). Date: 2026-06-13.*

---

## Executive Summary

**Purpose.** AutonomicLab is a Windows desktop application for clinical analysis of
Generalized Autonomic Testing (GAT) protocols. It loads physiological recordings from
Finapres NOVA beat-to-beat blood pressure monitors, runs standardized autonomic analysis
algorithms on three protocol types (Valsalva Maneuver, Deep Breathing, Stand Test),
presents interactive annotated plots allowing investigators to review and adjust computed
markers, and exports results to formatted Excel workbooks with embedded plot images.

**Scope.** The system covers data ingestion (two Finapres file formats), signal
processing, interactive result review, manual override and persistence, Excel/PNG
export, and role-based access control with centralized user management synchronized
via GitHub.

**Intended users.** Clinical investigators and physiologists at academic medical
institutions performing GAT protocols with the Finapres NOVA device. The application
is authored by Astrid Juhl Terkelsen (Aarhus University) and is distributed as a
Windows installer to collaborating sites worldwide. Three access roles are supported:
Admin, Investigator, and Guest (time-limited trial).

**Deployment context.** Packaged as a PyInstaller single-file Windows executable,
distributed via an Inno Setup installer hosted on GitHub Releases. Developed and
maintained on Linux; built for Windows via GitHub Actions on version tag push.

---

## Functional Requirements

### Data Loading

**FR-001** — The system shall load Finapres NOVA CSV datasets from a directory
containing semicolon-delimited CSV files with an 8-line header, where filenames
follow the pattern `{YYYY-MM-DD_HH.MM.SS} {SIGNAL}.csv`.

**FR-002** — The system shall auto-detect the datetime prefix from CSV filenames by
matching against known signal suffixes (`HR.csv`, `reBAP.csv`, `Markers.csv`). It
shall raise `FileNotFoundError` if no CSV files are found and `ValueError` if no
matching prefix can be determined.

**FR-003** — The system shall load the following CSV signals when present: `reBAP`,
`reSYS`, `reDIA`, `reMAP`, `HR`, `HR AP`, `HR SpO2`, `HR ECG (RR-int)`, `PAirway`,
`Resp Wave`, `HR ECG`, `ECG I`/`II`/`III`, `ECG aVR`/`aVL`/`aVF`/`C1`,
`PhysioCalActive`. Absent signals shall be silently skipped.

**FR-004** — The system shall parse CSV data rows atomically: a row whose value field
is blank or non-numeric shall be dropped in its entirety (both time and value columns)
to prevent time/value array length desynchronization.

**FR-005** — The system shall load Finapres NOVA binary `.nsc` files, which are ZIP
archives containing binary `.nsd` channel data files and a `Measurement.xml` metadata
file. The ZIP may contain a dated subdirectory prefix.

**FR-006** — For `.nsc` files, the system shall decode X-axis `.nsd` files as
`uint32` little-endian arrays (timestamps in 100 µs ticks) and Y-axis `.nsd` files as
`int16` little-endian arrays, scaled to physical units by:
`value = MinValue + raw_int16 × (MaxValue − MinValue) / 32767`.

**FR-007** — The system shall treat the Y-axis sentinel value `−32768` as an invalid
sample and replace it with `NaN`.

**FR-008** — The system shall detect gap / Physiocal-hold samples in `.nsc` channels
by flagging inter-sample intervals exceeding `max(500 ticks, 10 × expected_period_ticks)`,
setting those samples to `NaN`.

**FR-009** — The system shall read event markers from `.nsc` `Measurement.xml`,
converting absolute timestamps to seconds relative to `MeasurementBegin`, and
excluding markers where `Visible=False` or `MarkerType=Recording`.

**FR-010** — The system shall read protocol phase windows from `GATResults.xml` when
present inside the `.nsc` archive (Valsalva and Deep Breathing test regions with
`BeginTime`/`EndTime` attributes), numbering repeated tests sequentially
(e.g., `"Valsalva test 1"`). When `GATResults.xml` is absent, the system shall infer
windows from the first/last marker time per protocol phase.

**FR-011** — The system shall read event markers from `{PREFIX} Markers.csv` or
`{PREFIX}_TEST GAT Markers.csv` for CSV datasets.

**FR-012** — The system shall read phase region windows from
`{PREFIX}_RegionMarkers.csv` (semicolon-delimited `Start {name}` / `End {name}` label
pairs) for CSV datasets, returning a dict mapping region name to `(t_start, t_end)`.

**FR-013** — The system shall classify each marker label into one of four protocol
phases — Valsalva, Stand Test, Deep Breathing, or Other — by case-insensitive keyword
matching (`vm`/`valsalva`, `sm`/`stand`, `dbm`/`deep`/`breath`).

**FR-014** — The system shall present a three-button choice dialog ("CSV Folder" /
".nsc File" / Cancel) when the user initiates dataset opening, then open a
**native** file dialog (Qt's non-QGraphicsScene fallback must not be used) filtered
to the configured data folder.

**FR-015** — The system shall enable the "View Raw Data" button after any dataset
containing at least one ECG-family signal is loaded.

**FR-016** — The system shall enable the "View Embedded PDF" button when the loaded
`.nsc` archive contains any file with a `.pdf` extension; clicking it shall extract
the PDF to a temporary file and open it with the OS default PDF handler.

---

### Protocol Analysis

**FR-017** — The system shall implement the Valsalva Maneuver analysis algorithm per
Novak 2011 / Mayo Clinic protocol, computing all of the following from signals `reSYS`,
`HR`, and `PAirway`:

| Computed quantity | Description |
|---|---|
| `t_bl_s`, `t_bl_e` | Baseline window boundaries (s) |
| `t_S1s`, `t_S1e` | Phase I start/end |
| `t_S2es`, `v_nadir` | Phase IIe nadir time and SBP (mmHg) |
| `t_S2lmax`, `v_S2lmax` | Phase IIl max time and SBP (mmHg) |
| `t_S3s`, `t_S3e`, `v_S3min` | Phase III start/end and min SBP |
| `t_S4e` | Phase IV end |
| `avg_sbp` | Baseline mean SBP (mmHg) |
| `t_ov`, `v_ov` | SBP overshoot time and value |
| `hr_max_t`, `hr_max_v` | HR max time and value (bpm) |
| `hr_min_t`, `hr_min_v` | HR min time and value (bpm) |
| A | Baseline SBP − IIe nadir SBP (mmHg) |
| B | S2late max SBP − IIe nadir SBP (mmHg) |
| PRT | Pressure Recovery Time (s) |
| VR | Valsalva Ratio = HR max / HR min |
| BRSa | Baroreflex sensitivity = (A + 0.75×B) / PRT (mmHg/s) |

**FR-018** — Phase I start (`t_S1s`) shall be detected by finding the first upward
crossing of 0.5 mmHg in the `PAirway` signal after the Valsalva marker (`vm1`),
verified to reach ≥ 5 mmHg within the following 1 second.

**FR-019** — Phase III start (`t_S3s`) shall be detected by the first downward crossing
of 0.5 mmHg in `PAirway` after Phase I start.

**FR-020** — The baseline window shall default to `t_S1s − 45 s` through
`t_S1s − 15 s`. Manual "Phase X: End" markers in the recording shall override
algorithmic Phase I boundary detection.

**FR-021** — HR max shall be located within the window `[t_S2es, t_S3s + 5 s]`.

**FR-022** — HR min shall be located within `[hr_max_t, hr_max_t + 30 s]`.

**FR-023** — The system shall detect Finapres Physiocal-calibration interference via
the `PhysioCalActive` signal (value > 0.5 = active). Interference in the Baseline
window shall add a `"Baseline"` warning. Interference anywhere in the post-release
window `[t_S3s, t_S4e]` shall add a `"Phase III+IV"` warning **and** suppress all
post-release-dependent values (`t_S3e`, `v_S3min`, `t_S4e`, HR min, PRT, overshoot)
to prevent reporting unreliable derived parameters.

**FR-024** — The system shall implement Deep Breathing RSA analysis using
`scipy.signal.find_peaks` on the `HR` signal within the DBM2–DBM3 guided-breathing
window, with minimum peak prominence 3 bpm and minimum inter-peak distance 4 s.

**FR-025** — The system shall pair each detected HR peak with the first unused
subsequent trough to form an RSA cycle; ΔHR = HR_peak − HR_trough.

**FR-026** — The system shall select the top N=6 cycles by ΔHR and compute:
mean ΔHR for all valid cycles, mean ΔHR for top-N cycles, mean HR max/min for both
subsets.

**FR-027** — The system shall implement the Stand Test as a visualization-only phase
providing a two-panel BP/HR plot with event markers but no numerical analysis or
Excel export.

---

### Interactive Annotations and Manual Override

**FR-028** — The Valsalva analysis view shall render three vertically linked subplots
(Blood Pressure, Heart Rate, Airway Pressure) with color-coded phase fills matching
the Novak 2011 figure, measurement point dots, and annotated brackets for A, B, VR,
and PRT.

**FR-029** — The system shall render the Valsalva baseline as a draggable
`LinearRegionItem` on the BP subplot. Dragging shall update `avg_sbp`, the A bracket,
PRT annotation, and BRSa in real time without triggering a full replot.

**FR-030** — The following Valsalva measurement points shall be rendered as draggable
dots constrained within their physically valid time windows: `t_S1e`, `t_S2es`,
`t_S2lmax`, `t_S3e`, `t_ov`, `hr_max_t`, `hr_min_t`. Dragging any point shall
immediately recompute all downstream derived values.

**FR-031** — The Deep Breathing view shall render an interactive HR plot where RSA
cycle peak and trough points can be dragged, added, or deleted. Changes shall
recompute all RSA statistics immediately.

**FR-032** — When Physiocal calibration has suppressed Phase IV, the HR min point
shall be shown as a ghost "drag to confirm" dot, prompting the investigator to
manually confirm its position.

**FR-033** — The system shall persist manual overrides atomically to `overrides.json`
in the dataset folder (write to a `.json.tmp` sibling file, then `os.replace()`),
timestamped at ISO-8601 second precision, immediately after each interactive change.

**FR-034** — On dataset load, the system shall restore stored overrides for all phases
and re-apply them before rendering. The override indicator and "Reset to Auto" button
shall be visible whenever overrides are active for the current phase.

**FR-035** — On "Reset to Auto" (confirmed by the user), the system shall delete the
phase entry from `overrides.json`, re-run the algorithm, and remove the override
indicator.

---

### Phase Navigation

**FR-036** — The Phase selector dropdown shall be populated from the dataset's region
markers after loading, with "All" as the first item.

**FR-037** — Selecting "All" shall display a full-recording overview: three linked
subplots (BP, HR, PAirway) with event marker vertical lines.

**FR-038** — Selecting a named phase shall zoom the analysis view to the phase window
and invoke the registered analyzer/plotter for that protocol.

**FR-039** — The markers table shall filter to show only markers within the selected
phase window's time bounds.

---

### Export

**FR-040** — The system shall export Valsalva analysis results to a timestamped,
mode-tagged `.xlsx` file
`{dataset_folder_name}_valsalva_results_{YYYYMMDD_HHMMSS}_{mode}.xlsx`
inside a `results/` subfolder, with three sections: Phase Boundaries, Signal Points,
Derived Parameters (Novak 2011 / Mayo Clinic). Unavailable values (`None`) shall
appear as `"N/A"` with amber cell highlighting.

**FR-041** — The system shall export Deep Breathing RSA results to a timestamped
`.xlsx` file with a per-cycle table (HR max, HR max time, HR min, HR min time, ΔHR,
Top-N flag) and summary rows for all-cycles mean and top-N mean.

**FR-042** — The system shall capture the current pyqtgraph scene as a PNG image
and embed it in the exported Excel workbook (scaled to 80% of original pixel
dimensions).

**FR-043** — Export filenames shall include a mode tag (`auto` or `manual`) reflecting
whether any manual overrides were active at export time.

**FR-044** — If a file matching `*_{protocol}_*_{mode}.xlsx` already exists in the
`results/` folder, the system shall prompt the user to confirm overwriting before
proceeding.

---

### Raw Data Viewer

**FR-045** — The secondary Raw Data Viewer shall display the following signal groups
when available: BP waveforms (reBAP/reSYS/reDIA/reMAP), HR (HR AP, HR ECG RR-int),
PAirway, ECG leads (I/II/III/aVR/aVL/aVF/C1), and derived PTT (ms) when both HR AP
and HR ECG RR-int are present.

**FR-046** — All visible plot X-axes shall be linked; panning or zooming one plot
shall move all plots together. The X-range shall be preserved across checkbox toggle
operations.

**FR-047** — ECG lead plots shall display beat markers at the RR-interval timestamps,
interpolated to the ECG signal amplitude.

**FR-048** — The Raw Data Viewer left panel shall display signal metadata: sample
rate, amplitude resolution for ECG, beat count and average HR for HR AP.

**FR-049** — The viewer shall be built so that toggling checkboxes never creates or
destroys Qt widgets; only layout placement changes. All plots are created once at
initialization and shown/hidden thereafter.

---

### Authentication and User Management

**FR-050** — The system shall require users to authenticate before accessing the main
window on every launch, unless no user accounts exist.

**FR-051** — The system shall support three roles:

| Role | Access |
|---|---|
| Admin | Full access + Admin menu (user management) |
| Investigator | Full analysis, override, and export access |
| Guest | Full analysis access; limited to a fixed launch count per machine |

**FR-052** — Guest access shall be limited to 10 launches per machine. The counter
shall be stored in a `guest_counter.json` file, MAC-address-bound and
HMAC-SHA256-signed. A signature mismatch shall reset the counter to 0; a MAC mismatch
shall reset the counter to 10 (new machine).

**FR-053** — The system shall bypass the login dialog and proceed directly to the main
window when `users.db` contains no user accounts (first-run setup mode).

**FR-054** — The "Continue as guest" button shall be hidden when `allow_guest: false`
is set in `config.yaml`, or when guest launches are exhausted.

**FR-055** — The Admin Panel (accessible only to admin-role users via the Admin menu)
shall support: add user (username, display name, role, password with confirmation),
edit display name/role, change password, enable/disable account, delete account
(with confirmation).

**FR-056** — On every launch (when online), the system shall fetch `users.db` from
the private GitHub repository `John-H-Aal/autonomiclab-users` via the Contents API
using the read-only PAT in `config.yaml`, replacing the local file if different.
Failures (offline, token invalid) shall be silently logged and skipped.

**FR-057** — When the Admin Panel is closed, the system shall push the local `users.db`
to the GitHub repository using the write-capable admin PAT. If the admin PAT is absent,
a first-time dialog shall prompt for it and save it to `config.yaml`. Push failure
shall display a warning but not revert local changes.

---

### Startup and Configuration

**FR-058** — The system shall display a branded splash screen for 2.5 seconds at
startup, with the application version overlaid on the splash image.

**FR-059** — The system shall write all log output (including DEBUG-level entries) to
`autonomiclab.log` next to the executable (installed) or in the project root
(development). Log rotation is not required.

**FR-060** — The system shall install a global exception hook that suppresses
`RuntimeError` exceptions containing the word `"deleted"` (pyqtgraph stale C++ object
errors) with a WARNING log entry, while re-raising all other unhandled exceptions.

**FR-061** — Admin configuration (`data_folder`, `users_db_token`, `users_db_admin_token`,
`allow_guest`) shall be read from `config.yaml` next to the executable. Per-user
preferences (`data_folder` override, `ui_zoom`) shall be read from
`~/.autonomiclab/settings.yaml`.

**FR-062** — The default data folder shall be `~/Documents/AutonomicLab/data`, with
user preferences able to override it, which in turn may be overridden by `config.yaml`.

---

## Non-Functional Requirements

### Performance

**NFR-001** — The system shall load a complete Finapres CSV recording session
(all available signals, markers, and region markers) within 10 seconds on a typical
Windows 10/11 workstation.

**NFR-002** — Switching between protocol phases shall render the analysis plot within
3 seconds of the user's selection.

**NFR-003** — Dragging a measurement point or baseline region shall update all
dependent annotations and recompute derived values within one display refresh cycle
(≤ 33 ms at 30 Hz), without triggering a full scene repaint.

### Reliability

**NFR-004** — Override files shall survive application crashes. The atomic rename
pattern (write to `.tmp` then `os.replace()`) shall ensure a crash mid-write leaves
the previous state intact rather than a partial file.

**NFR-005** — The system shall function without network connectivity, using the
locally cached `users.db` for login. Sync failures shall not block startup.

**NFR-006** — The system shall log and continue when individual CSV rows, marker files,
override files, or `.nsd` channel files are malformed, rather than aborting the load.

**NFR-007** — Plot resize events shall be debounced with a 50 ms `QTimer.singleShot`;
re-entrancy guards and `processEvents()` calls shall not be used as resize crash
mitigations (known to be ineffective for the specific pyqtgraph `ViewBox` crash).

### Security

**NFR-008** — User passwords shall be stored as bcrypt hashes using `bcrypt.gensalt()`
default work factor. No plaintext passwords shall be persisted anywhere.

**NFR-009** — The `users.db` SQLite file shall store all sensitive user fields
(display name, password hash, created_at) as Fernet-AES-256-encrypted JSON blobs.
The Fernet key shall be derived via PBKDF2-HMAC-SHA256 (100,000 iterations, static
application salt) from a static application secret baked into the binary.

**NFR-010** — The guest counter file shall be HMAC-SHA256 signed with a key derived
from the application secret and the machine MAC hash. Any tampering invalidates the
signature and resets the counter to 0.

**NFR-011** — The write-capable admin GitHub PAT (`users_db_admin_token`) shall not
be included in the distributed installer or checked into the public repository.

### Portability

**NFR-012** — The distributed application shall run on Windows 10 (64-bit) and
Windows 11 without requiring installation of Python or any runtime dependencies.

**NFR-013** — The installer shall require only user-level privileges
(`PrivilegesRequired=lowest`). The default installation directory shall be
`%LOCALAPPDATA%\AutonomicLab`.

**NFR-014** — The build pipeline shall run on a `windows-latest` GitHub Actions
runner using Python 3.12 and PyInstaller `--onefile --windowed`.

### Maintainability

**NFR-015** — The GUI layer (`MainWindow`) and orchestration layer (`AppController`)
shall be separated via a `WindowProtocol` structural typing protocol. `AppController`
shall only call `MainWindow` through methods declared in that protocol.

**NFR-016** — Signal processing algorithms shall reside exclusively in the `analysis/`
package. Drawing code shall reside exclusively in the `plotting/` package. Neither
package shall import from the other.

**NFR-017** — Font sizes, font weights, and layout proportions shall be externalized
to `autonomiclab/config/fonts.yaml` and loaded at runtime by `FontLoader`.

### Scalability

**NFR-018** — The system shall correctly load and display Finapres recordings up to
at least 1,500 seconds (25 minutes) in length without memory errors or UI freezes.

---

## Interface Requirements

### Hardware Interfaces

**IR-001** — The system consumes data files produced by the Finapres NOVA blood
pressure monitor (Model 4 series). No direct hardware connection or driver is
required; all data access is via files on disk.

### External Service Interfaces

**IR-002** — The system shall use the GitHub Contents REST API
(`GET /repos/{owner}/{repo}/contents/{path}`,
`PUT /repos/{owner}/{repo}/contents/{path}`) for user database synchronization.
Authentication shall use GitHub Personal Access Tokens as `Authorization: token {pat}`
headers. The `Accept: application/vnd.github+json` header shall be included. Network
timeout shall be 10 seconds.

### File Format Interfaces

**IR-003** — **Finapres CSV format:**
- Encoding: UTF-8 with error replacement
- Delimiter: semicolon (`;`)
- Header: 8 lines (skipped)
- Data rows: `{time_seconds};{value};`
- Filename pattern: `{YYYY-MM-DD_HH.MM.SS} {SIGNAL}.csv`

**IR-004** — **Finapres NOVA `.nsc` binary format:**
- Container: ZIP archive (optionally with a `{YYYY-MM-DD_HH.MM.SS}/` internal prefix)
- `Measurement.xml`: channel metadata (`SignalContainer/ModelSignals/Signal` elements;
  `ShortName`, `DataFile`, `Units`, `SampleRate`, `MinValue`, `MaxValue`, `Type`);
  `MeasurementBegin` absolute timestamp; `Markers` elements
- `GATResults.xml` (optional): `Valsalva` and `DeepBreathingTest` elements with
  `Results[@BeginTime]` and `Results[@EndTime]` attributes
- X-axis `.nsd`: `uint32` LE, 100 µs/tick
- Y-axis `.nsd`: `int16` LE, sentinel `−32768` = invalid;
  scale: `physical = MinValue + raw × (MaxValue − MinValue) / 32767`
- Embedded PDF (optional): any entry with `.pdf` extension

**IR-005** — **Marker CSV format:**
- Rows: `{time_seconds};{label}`
- Header row (starting with "time") is skipped

**IR-006** — **RegionMarkers CSV format:**
- Same encoding and delimiter as markers
- Label pairs: `Start {region_name}` / `End {region_name}`

**IR-007** — **`overrides.json` format:**
```json
{
  "{phase_name}": {
    "t_bl_s": <float>,
    "t_bl_e": <float>,
    "points": {"t_S1e": <float>, ...},
    "cycles": [{"cycle": <int>, "max_t": <float>, "min_t": <float>}, ...],
    "saved_at": "YYYY-MM-DDTHH:MM:SS"
  }
}
```

**IR-008** — **`config.yaml` format:**
```yaml
data_folder: "<path>"
users_db_token: "github_pat_..."
users_db_admin_token: "github_pat_..."
allow_guest: true|false
```

**IR-009** — **`guest_counter.json` format:**
```json
{"mac_hash": "<sha256hex>", "remaining": <int>, "sig": "<hmac256hex>"}
```

**IR-010** — **Excel export format:** `.xlsx` (OpenXML), compatible with Microsoft
Excel 2010+. No VBA macros. Plot images embedded as PNG drawings via openpyxl.

### Output Interfaces

**IR-011** — The system shall open PDF files using the platform default PDF handler
via `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`.

**IR-012** — The system shall open the release URL
`https://github.com/John-H-Aal/autonomiclab/releases/latest` in the system browser
from Help → User Guide.

---

## Constraints and Assumptions

**C-001** — The Valsalva and Deep Breathing algorithms implement the Novak 2011 /
Mayo Clinic protocol. Clinical interpretation of all computed parameters is the
sole responsibility of the investigator.

**C-002** — The CSV parser assumes semicolons as the delimiter and dots as the
decimal separator. Finapres exports from European locales that use semicolons as
decimal separators may silently produce empty or incorrect signals (see OQ-009).

**C-003** — All time values in CSV files are assumed to be in seconds. No time-unit
metadata field is parsed; this assumption is based on observed Finapres NOVA export
behavior.

**C-004** — The encryption key for `users.db` is a static value baked into the
binary. This prevents casual file editing (defense-in-depth) but does not protect
against an adversary with access to the binary and a disassembler.

**C-005** — The GitHub-based user sync model requires the administrator to control
the `John-H-Aal/autonomiclab-users` private repository.

**C-006** — The guest counter is bound to the machine MAC address via `uuid.getnode()`.
A user who changes their MAC address, uses a virtual machine with a configurable MAC,
or copies the counter file from another machine may circumvent the limit. This is an
accepted risk for a low-stakes trial mechanism.

**C-007** — The data folder must be on a locally accessible filesystem with write
access for `overrides.json` and the `results/` export directory.

**C-008** — The `PhysioCalActive` calibration guard is only available when the signal
is present in the loaded dataset. Absence of this signal for CSV-format recordings
is handled gracefully (no warnings emitted), but calibration interference in those
recordings will go undetected.

**C-009** — The Stand Test analysis is intentionally incomplete. `StandAnalyzer`
returns an empty result and `StandPlotter` renders BP/HR visualization only, with no
`export()` method. The Export Excel button is disabled for Stand Test phases.

---

## Open Questions / Gaps

**OQ-001 — Stand Test export crash** *(resolved v1.1.0)*
`StandPlotter` has no `export()` method; calling `export_current()` for a Stand Test
phase would raise `AttributeError`. Fixed by gating `set_export_enabled(True)` on
`protocol_key in ("valsalva", "deep breath")` — the Export Excel button stays disabled
for Stand Test. The underlying numerical analysis gap (OQ-001 original scope) remains:
`StandAnalyzer.analyze()` returns an empty `StandResult` with no computed metrics.

**OQ-002 — Allowed-users list** *(resolved v1.1.0 — removed)*
`AppSettings.allowed_users` was a dead property: never read by any caller, absent from
`config.yaml`, and superseded by the role system. Removed from `AppSettings`.

**OQ-003 — UI zoom setting not applied at startup** *(resolved v1.1.0)*
`FontLoader.set_zoom(self._settings.ui_zoom)` is now called in `MainWindow.__init__`
before `_init_ui()`, so a value set in `~/.autonomiclab/settings.yaml` takes effect
across all widget font sizes at startup. See OQ-011 for the remaining gap.

**OQ-004 — NSC files and protocol markers**
The User Guide states ".nsc files do not contain protocol markers." The code does read
markers from `Measurement.xml` and region windows from `GATResults.xml`. The guide
statement applies only to recordings that have not been processed through the Finapres
GAT software (no `GATResults.xml` present). User-facing documentation should be
updated to clarify this distinction.

**OQ-005 — Multiple Valsalva tests per session** *(latent bug — deferred)*
Region parsing and phase dispatch are structurally correct for multi-test sessions.
Each named phase (`"Valsalva test 1"`, `"Valsalva test 2"`) gets its own
`(t_start, t_end)` window, its own override key, and its own marker-filtered analysis
call. However: when no `vm1` marker falls within a test's window,
`ValsalvaAnalyzer.analyze()` previously fell back to `t_pa[0]` (start of the entire
recording) as `t_anchor`, causing `_pa_cross` — which has no upper bound — to find
PAirway crossings from the *previous* test. Fixed in v1.1.0: fallback is now
`t_start if t_start is not None else t_pa[0]`, so unmarkered tests anchor to their own
window. Requires validation against real multi-test clinical recordings.

**OQ-006 — ECG-derived HR not used in Valsalva analysis**
`ValsalvaAnalyzer` uses only the `HR` (Finapres AP-derived) signal for HR max/min
and VR. `HR ECG (RR-int)` is loaded and displayed in the Raw Data Viewer but is
never selected as an alternative source. Whether this exclusion is intentional
(ECG-derived HR preferred, or not — clinically they may differ significantly during
a Valsalva) is undocumented.

**OQ-007 — Locale sensitivity of CSV float parsing**
`float("1,5")` raises `ValueError`, causing the row to be silently dropped. If a
Finapres installation on a European-locale Windows system exports CSVs with
comma-as-decimal-separator, the entire signal would load as empty. No test covers
this case and no error is surfaced to the user.

**OQ-008 — PhysioCalActive absent for CSV datasets**
When `PhysioCalActive` is not available (CSV format or older NOVA firmware), the
Valsalva analyzer produces no calibration warnings. No notice is given to the
investigator that calibration protection was unavailable. This is a silent risk.

**OQ-009 — Live PATs in repository**
The committed `config.yaml` (in the development repository) contains live GitHub PAT
values. These should be rotated and replaced with placeholder comments before any
public exposure of the repository, and the values should be stored only in CI secrets
and on production machines.

**OQ-010 — Installer password optional**
The Inno Setup installer supports AES encryption when `INSTALLER_PASSWORD` CI secret
is set. If the secret is absent, the installer is built without encryption. No
policy requirement on whether installation encryption is mandatory is documented.

**OQ-011 — UI zoom is a power-user-only setting**
`ui_zoom` is now read and applied at startup (OQ-003 resolved), but it is only
configurable by manually editing `~/.autonomiclab/settings.yaml`. No UI control
exists. Investigators who need larger fonts have no in-app way to discover or change
this setting. Options: add a zoom slider or spin-box to the left panel (requires
reapplying stylesheets at runtime), or document the setting explicitly in the User
Guide under a "Accessibility / Display" section.
