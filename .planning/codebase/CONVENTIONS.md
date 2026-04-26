# Coding Conventions

**Analysis Date:** 2026-04-26

## Language & Version

- **Python 3.9+** (`setup.py` declares `python_requires=">=3.9"`); dev environment runs Python 3.13
- `from __future__ import annotations` used in 36/50 modules for PEP 604 union syntax compatibility
- Type hints are mandatory on public functions and dataclass fields; `list[Marker]`, `dict[str, Signal]`, `Path | None` style preferred (PEP 604)

## Module Layout Convention

Every non-trivial module follows this exact ordering:

```python
"""One-line module docstring.

Optional longer description.
"""

from __future__ import annotations

import stdlib_module                      # stdlib first
from pathlib import Path

import third_party                         # third-party next
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QMainWindow

from autonomiclab.core.models import ...   # first-party absolute imports last
from autonomiclab.utils.logger import get_logger

log = get_logger(__name__)                 # module-level logger first thing after imports

_PRIVATE_CONSTANT = 0.5                    # module constants prefixed with `_`
```

Reference: `autonomiclab/gui/app_controller.py:1-26`, `autonomiclab/core/finapres_loader.py:1-13`.

## Naming Patterns

**Files:**
- snake_case: `app_controller.py`, `dataset_service.py`, `finapres_loader.py`
- Per-protocol modules in `analysis/` and `plotting/`: `valsalva.py`, `deep_breathing.py`, `stand.py` (kept symmetrical across both packages so `registry.py` can pair them)

**Classes:**
- PascalCase: `DatasetService`, `ValsalvaAnalyzer`, `ValsalvaPlotter`, `MainWindow`, `AppController`, `AppState`
- Result dataclasses end in `Result`: `ValsalvaResult`, `DeepBreathingResult`, `StandResult`
- Analyzer/Plotter pairs follow `<Protocol><Role>` (e.g., `ValsalvaAnalyzer` + `ValsalvaPlotter`)
- Private/internal classes prefixed with `_`: `_ComboDelegate` (`gui/main_window.py:36`), `_UserFormDialog` (`gui/auth/admin_panel.py:203`)

**Functions / methods:**
- snake_case: `load_csv_signal`, `detect_datetime_prefix`, `phase_window`, `resolve_protocol`
- Private/helper methods prefixed with `_`: `_init_ui`, `_load`, `_save`, `_make_section_header`
- Qt event overrides keep PyQt camelCase: `closeEvent`, `keyPressEvent`, `showEvent`, `mousePressEvent`, `initStyleOption`

**Variables:**
- snake_case for locals/attributes; instance attrs that should not be touched outside the class are `_`-prefixed: `self._state`, `self._ctrl`, `self._svc`
- Module-level constants UPPER_SNAKE_CASE with leading underscore when private to the module: `_THRESH`, `_FILL`, `_FMT`, `_DEFAULT_LAUNCHES`, `_NSC_SIGNALS`, `_PROTOCOL_SLUG`

**Type aliases / Protocols:**
- PascalCase: `WindowProtocol` (`gui/app_controller.py:40`), `BaselineOverrideCallback`, `PointOverrideCallback` (in `core/protocols.py`)

## Type Hints

- All public functions return-annotated. `-> None` is explicit, never omitted.
- `Optional[X]` and `X | None` both appear; `X | None` is preferred in newer code (`gui/app_state.py:18`, `__main__.py:39`).
- Forward references handled via `from __future__ import annotations` plus `if TYPE_CHECKING:` for circular-import avoidance (`gui/app_controller.py:23`).

## Architectural Patterns

### Registry pattern
`autonomiclab/plotting/registry.py` is the canonical example: a module-level `PROTOCOL_REGISTRY: dict[str, dict[str, Any]]` maps a protocol key (`"valsalva"`, `"stand"`, `"deep breath"`) to an `{"analyzer": ..., "plotter": ...}` pair. `resolve_protocol(phase_name)` does keyword matching on phase strings. New protocols are added by:
1. Implementing analyzer in `autonomiclab/analysis/<protocol>.py`
2. Implementing plotter in `autonomiclab/plotting/<protocol>.py`
3. Registering both in `PROTOCOL_REGISTRY` and adding a keyword in `_KEYWORDS`

### Singleton state via `AppState` dataclass
`autonomiclab/gui/app_state.py` defines a `@dataclass` instantiated **once** in `MainWindow.__init__` and passed by reference into `AppController`. Both objects mutate the same `AppState`; no callbacks or signals are used to synchronize. Do not copy `AppState` — pass it.

### Module-level singleton (auth session)
`autonomiclab/auth/session.py` uses module-global `_current_user: User | None` with `login()` / `logout()` / `current_user()` / `is_admin()` / `is_guest()` accessors. Do not store the user on `AppState` — read it from `auth.session`.

### Protocol-based decoupling
`AppController` accepts a `WindowProtocol` (structural type, `gui/app_controller.py:40`) rather than a concrete `MainWindow`. This breaks the import cycle: `MainWindow` constructs `AppController`, but `AppController` only sees the protocol. Use this pattern when introducing a new orchestrator that must call back into a Qt widget.

### Analyzer / Plotter / Result triad
Each protocol splits into three artifacts:
- `*Result` — frozen-ish `@dataclass` of computed values + key timestamps (e.g., `ValsalvaResult`, `analysis/valsalva.py:23`)
- `*Analyzer` — pure signal processing, no Qt; `analyze(dataset, markers, **kwargs) -> *Result`
- `*Plotter` — drawing only; `plot(plot_widget, dataset, result, t_start, t_end, **callbacks)`

Analyzers must not import `pyqtgraph` or `PyQt6`. Plotters must not duplicate analyzer math.

## Dataclasses

Used heavily for value objects (11 occurrences). Conventions:
- `@dataclass` (not `frozen=True`) — these objects are mutated by the controller when overrides are applied
- Mutable defaults via `field(default_factory=dict)` / `field(default_factory=list)` — never bare `[]` / `{}`
- `__post_init__` used for validation/normalization (e.g., `Signal.__post_init__` truncates mismatched arrays at `core/models.py:23-32`)
- `__bool__` overridden when emptiness is meaningful (`Signal.__bool__` returns `len(times) > 0`, `core/models.py:42`)

## Code Style

**Formatting:**
- No formatter configured (`black`, `ruff`, etc. not in `requirements-dev.txt`)
- House style: 4-space indent, ~100-column soft wrap, trailing commas in multi-line literals
- Vertical alignment of dict / kwargs values is common (`gui/main_window.py:412-417`, `analysis/valsalva.py:27-37`) — preserve when editing nearby lines

**Linting:**
- No linter configured. Code review is the only gate.

**Section dividers:**
Files use ASCII box-drawing comment headers to separate logical sections:
```python
# ── public API ───────────────────────────────────────────────────────────
```
Reference: `auth/guest_counter.py:28`, `gui/main_window.py:95`. Use these when a module exceeds ~80 lines.

## Import Organization

Three groups, blank-line-separated, in this order:
1. Standard library
2. Third-party (`numpy`, `pyqtgraph`, `PyQt6`, `bcrypt`, `yaml`, `openpyxl`)
3. First-party (`autonomiclab.*`) — always absolute, never relative

Inside each group: `import X` before `from X import Y`. Imports are alphabetized within their `from` clauses where feasible.

**Lazy imports:** Heavy or circular imports are deferred to function bodies (`__main__.main` defers `MainWindow` import until after logger is configured; `MainWindow._show_admin_panel` defers `AdminPanel` import to keep startup fast).

## Error Handling

**Module-level logger pattern:**
```python
from autonomiclab.utils.logger import get_logger
log = get_logger(__name__)
```
Used in 27 modules. Single exception is `core/models.py:12` which uses `_log = logging.getLogger(__name__)` directly to avoid pulling utils on import.

**Try/except idioms:**
- 93 `try`/`except` occurrences across the package
- Loaders return `None` on missing-file rather than raise (`finapres_loader.load_csv_signal:71`, `markers_handler.load_markers`)
- Service-layer methods raise `FileNotFoundError` for explicit invocation (`DatasetService.load`)
- Controller catches **broad** `Exception` at orchestration boundaries and logs via `log.exception(...)` to record traceback, then surfaces a user-friendly message via `WindowProtocol.set_status("error", ...)` and `show_message(...)`. Reference: `gui/app_controller.py:230-233`, `gui/app_controller.py:311-314`.
- `log.error(...)` is for known-failure paths with a useful message; `log.exception(...)` is for "this should not have happened, give me the traceback".

**pyqtgraph stale C++ object errors are SWALLOWED globally:**
`autonomiclab/__main__.py:21-36` installs a custom `sys.excepthook` that detects `RuntimeError` containing the substring `"deleted"` and logs it as a warning instead of crashing. These come from pyqtgraph holding references to Qt C++ objects that Qt has already destroyed. **Do not chase these errors during debugging.** They are expected and harmless, but they MUST be prevented from propagating to the OS-level abort path. When you write code that touches a `pg.PlotItem`, `pg.InfiniteLine`, or scene item across a `clear()` boundary, wrap defensive removals in `try/except Exception: pass` (see `gui/widgets/interactive_plot.py:82-86`, `gui/widgets/interactive_plot.py:131-137`).

**Plot resize / ViewBox crashes:**
The fix is `QTimer.singleShot(50, ...)` debouncing. `processEvents()` and re-entrancy guards do not work. Reference: `gui/close_mixin.py:27`, `plotting/deep_breathing_cycles.py:169-174`.

**Defensive try/except inside loops:**
When iterating over Qt items that may have been deleted, the inner block is wrapped:
```python
try:
    if line.scene() is scene:
        scene.removeItem(line)
except Exception:
    pass
```
Reference: `gui/widgets/interactive_plot.py:131-137`. Bare `except:` is never used; it's always `except Exception:`.

## Logging

**Framework:** stdlib `logging`, configured once in `autonomiclab/utils/logger.py`.

**Setup:**
- `configure_root_logger(log_file=...)` called exactly once from `__main__.main` before any module logger is used
- Format: `%(asctime)s  %(levelname)-8s  %(name)s  %(message)s` with `%H:%M:%S` time
- Level: `DEBUG` by default, both `StreamHandler` (console) and `FileHandler` (`autonomiclab.log` next to project root or `.exe`)
- Re-entrant: `if root.handlers: return` so duplicate calls are no-ops

**Per-module usage:**
```python
log = get_logger(__name__)        # at module top
log.debug("Detected prefix: %s", prefix)
log.info("Loading dataset from %s (prefix: %s)", folder, prefix)
log.warning("Signal '%s': times(%d) vs values(%d) length mismatch", name, nt, nv, n)
log.error("Failed to load dataset: %s", exc)
log.exception("Plot error: %s", exc)   # in except blocks where traceback matters
log.critical("Unhandled exception:\n%s", msg)   # only in __main__ excepthook
```

**Style rules:**
- Always use `%`-style placeholders, never f-strings, so the log framework can skip formatting when the level is disabled
- One log line per significant event; do not log inside tight loops
- Include identifying context (path, name, count) in every log message
- Never log secrets — bcrypt hashes are fine, raw passwords never reach a logger anyway because they're consumed inline by `bcrypt.checkpw`

**Log file:** `autonomiclab.log` in project root (dev) or next to `AutonomicLab.exe` (installed). Resolved by `__main__._log_path()`.

## Comments

**When to comment:** Only when *why* is non-obvious. Code should explain *what*; comments explain *why this approach over the alternatives*. Examples of good comments:
- `gui/main_window.py:343-345` — explains why native Windows file dialog is required (Qt fallback crashes pyqtgraph)
- `gui/widgets/interactive_plot.py:124-130` — explains why `clear()` must remove items manually before super
- `__main__.py:24-27` — explains why the excepthook swallows certain RuntimeErrors

**Docstrings:**
- Module docstrings: one-line summary, optional longer description. Always present.
- Class docstrings: present on every public class.
- Function docstrings: present on public functions; reST-style `Parameters` / `Raises` blocks used in `gui/app_controller.py:56-68`.
- Private `_helpers` typically have no docstring — the name is the documentation.

## Function Design

- Most functions stay under ~30 lines. Larger ones (e.g., `MainWindow._init_ui` at ~180 lines) build UI declaratively and are an accepted exception.
- Keyword-only arguments are not enforced via `*`, but optional parameters always have defaults.
- Returning `Optional[X]` / `X | None` for "not found" is preferred over raising for loaders; raising is reserved for service-layer entry points.

## Module Design

- One responsibility per module. `analysis/<protocol>.py` is pure math, `plotting/<protocol>.py` is pure drawing, `core/<thing>_loader.py` parses one file format.
- No barrel `__init__.py` re-exports. Sub-package `__init__.py` files are empty or contain only the version string (`autonomiclab/__init__.py`).
- Cross-module communication goes through `AppController`. Widgets do not import each other.

## PyQt6 Idioms

- Always import enums via their full path: `Qt.AlignmentFlag.AlignCenter`, `QMessageBox.StandardButton.Yes`, `QPalette.ColorRole.Text`. The legacy `Qt.AlignCenter` form does not work in PyQt6.
- Stylesheets are stored as module-level f-string templates (`_PRIMARY_BTN`, `_SECONDARY_BTN` in `gui/main_window.py:46-74`) and `.format(...)`-applied per widget.
- Signals are connected with `widget.signal.connect(self._handler)` — never with lambdas that capture loop variables without a default-argument freeze (`lambda t0, t1, p=phase: ...` pattern in `gui/app_controller.py:208`).
- `blockSignals(True/False)` used to suppress combo-box callbacks during programmatic repopulation (`gui/main_window.py:401-405`).
- `QTimer.singleShot(0, callable)` is the standard "defer to next event loop iteration" idiom.

---

*Convention analysis: 2026-04-26*
