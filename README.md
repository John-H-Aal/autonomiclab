# AutonomicLab - Complete File Structure & Installation Guide

## Project Overview
AutonomicLab is a PyQt6 GUI application for analyzing Finapres NOVA GAT protocol data (Valsalva, Stand Test, Deep Breathing).

**Status**: ✅ Production Ready
**Technology**: PyQt6, matplotlib, numpy, scipy, pandas, PyYAML
**Python**: 3.9+

---

## Installation & Setup

### 1. Create Virtual Environment
```bash
cd ~/Projects/Python/AutonomicLab
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python -m autonomiclab
```

---

## Project Structure

```
AutonomicLab/
├── autonomiclab/                 # Main package
│   ├── __init__.py              # Package metadata
│   ├── __main__.py              # Entry point
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── font_loader.py       # Load fonts from YAML config
│   │   └── fonts.yaml           # Font configuration (CUSTOMIZE HERE)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── finapres_loader.py   # Load CSV signals (auto-detect prefix)
│   │   ├── markers_handler.py   # Parse markers, determine phase
│   │   ├── gat_analyzer.py      # Main GAT analysis engine
│   │   └── signal_processor.py  # Filtering, artifact detection
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py       # Main PyQt6 window (FULL FEATURED)
│   │   ├── dialogs.py           # File dialogs
│   │   ├── widgets.py           # Custom widgets
│   │   └── styles.py            # Qt stylesheets
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── dataset.py           # DataSet class
│   │   ├── signal.py            # Signal class
│   │   └── markers.py           # Marker parsing
│   │
│   ├── plotting/
│   │   ├── __init__.py
│   │   └── plotter.py           # GATPlotter class (zoom/pan support)
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── valsalva.py          # Valsalva analyzer
│   │   ├── stand_test.py        # Stand Test analyzer
│   │   ├── deep_breathing.py    # Deep Breathing analyzer
│   │   └── hrv_analysis.py      # HRV analyzer
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── font_config.py       # Legacy font config (deprecated)
│   │   ├── logger.py            # Logging setup
│   │   └── config.py            # App constants
│   │
│   ├── resources/
│   │   └── icons/               # Button icons (placeholder)
│   └── models/
│       └── dataset.py
│
├── requirements.txt              # Python dependencies
├── setup.py                      # Package installation config
├── README.md                     # Project documentation
└── LICENSE                       # MIT License
```

---

## Key Files Explanation

### `main_window.py` - Main Application Window
- **Features**:
  - Full-screen PyQt6 GUI
  - Left sidebar: 240px (markers table, filters, zoom controls)
  - Right side: Plot area (matplotlib canvas)
  - UI Zoom: 50-200% (font scaling)
  - Signal Zoom: 0.1x-10.0x (time axis zoom)
  - Pan controls: ◀ Pan Left, ▶ Pan Right
  - Interactive dataset loading with QFileDialog
  - Real-time plot updates

- **Key Methods**:
  - `init_ui()`: Build UI layout
  - `on_ui_zoom_changed()`: Handle UI font zoom
  - `on_signal_zoom_changed()`: Handle signal zoom
  - `pan_left()/pan_right()`: Pan through signal
  - `plot_current_phase()`: Render plot with zoom/pan
  - `load_dataset()`: Auto-detect prefix & load signals

### `plotter.py` - Plotting Engine
- **Features**:
  - 3 plotting methods: Valsalva, Stand Test, Deep Breathing
  - Custom zoom/pan logic (PyQt6-friendly, no matplotlib toolbar)
  - Automatic marker line overlay
  - Synchronized x-axis across subplots
  - Font configuration from YAML

- **Key Methods**:
  - `apply_zoom_pan()`: Calculate zoomed time ranges
  - `create_valsalva_plot()`: BP + HR + PAirway
  - `create_stand_test_plot()`: BP + HR
  - `create_deep_breathing_plot()`: HR + Resp Wave

### `finapres_loader.py` - Data Loading
- **Features**:
  - Auto-detect datetime prefix from CSV files
  - Load signals from semicolon-separated CSVs
  - Skip header rows (default: 8)
  - Robust error handling

- **Key Methods**:
  - `detect_datetime_prefix()`: Find prefix from first CSV
  - `load_csv_signal()`: Load time/value pairs

### `markers_handler.py` - Marker Parsing
- **Features**:
  - Parse markers.csv files
  - Auto-categorize by phase (Valsalva/Stand Test/Deep Breathing)
  - Handle marker label parsing

- **Key Methods**:
  - `load_markers()`: Load all markers from CSV
  - `determine_phase()`: Classify marker by label

### `font_loader.py` - Font Configuration
- **Features**:
  - Load font sizes from YAML config
  - Apply zoom factor (50-200%)
  - Auto-generate QSS stylesheets
  - Persistent storage of UI zoom level

- **Key Methods**:
  - `load()`: Load fonts.yaml
  - `get()`: Get font size for element
  - `style()`: Generate CSS style string
  - `set_zoom()/save_zoom()`: Persist zoom level

### `fonts.yaml` - Font Configuration File
```yaml
left_panel:
  title:
    size: 13
    weight: bold
  button:
    size: 12
    weight: bold
  filter_combo:
    size: 13
    weight: bold
  # ... more elements

plot_panel:
  title:
    size: 15
    weight: bold
  ylabel:
    size: 14
    weight: bold
  # ... more elements

ui_zoom: 100
```

**CUSTOMIZE HERE** to adjust font sizes!

---

## Features & Usage

### Zoom Controls
1. **UI Zoom** (50-200%):
   - Adjusts all interface fonts
   - Saves automatically to `fonts.yaml`
   - Quick access with Reset button

2. **Signal Zoom** (0.1x-10.0x):
   - Zoom IN/OUT on time-series data
   - X-axis updates dynamically
   - All 3 subplots zoom together

3. **Pan Controls**:
   - `◀` Pan Left: Move view backward
   - `▶` Pan Right: Move view forward
   - Smooth navigation through long signals

### Filter & Markers
- **Phase Filter**: Select test type (Valsalva/Stand/Breathing)
- **Markers Table**: Sortable, shows time + label
- **Dataset Info**: Summary of loaded protocol

### Data Loading
1. Click **Select** button
2. Navigate to Finapres dataset folder (contains `*Markers.csv` + signal CSVs)
3. App auto-detects datetime prefix
4. Signals load automatically
5. Select phase from dropdown

---

## Dataset Requirements

**Finapres NOVA CSV Format:**
- Prefix: `2025-09-10_09.04.59` (datetime format with underscore)
- Signals: `{PREFIX} reBAP.csv`, `{PREFIX} HR.csv`, `{PREFIX} PAirway.csv`, `{PREFIX} Resp Wave.csv`
- Markers: `{PREFIX} Markers.csv`
- Format: Semicolon-separated, 8-line header, time;value columns

**Example Dataset:**
```
2025-09-10_09.04.59 Markers.csv
2025-09-10_09.04.59 reBAP.csv
2025-09-10_09.04.59 HR.csv
2025-09-10_09.04.59 PAirway.csv
2025-09-10_09.04.59 Resp Wave.csv
```

---

## Configuration

### Font Configuration (`fonts.yaml`)
Edit `autonomiclab/config/fonts.yaml` to customize all font sizes:
- Increase font size for presentation mode
- Adjust colors in stylesheet definitions
- Persistent storage of UI zoom level

### Requirements (`requirements.txt`)
```
PyQt6>=6.4.0
matplotlib>=3.7.0
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
pytz>=2023.3
PyYAML>=6.0
```

---

## Development Notes

### Architecture
- **Clean separation**: GUI (PyQt6) ↔ Business Logic (NumPy/Signal Processing) ↔ Data (CSV loaders)
- **No matplotlib toolbar**: Custom PyQt6 controls handle zoom/pan
- **Font-first design**: All fonts centralized in YAML
- **Error handling**: Graceful degradation with status messages

### Adding New Features
1. **New analyzer**: Add `autonomiclab/analysis/my_test.py`
2. **New plot type**: Add method to `GATPlotter` in `plotter.py`
3. **Font changes**: Edit `fonts.yaml` (no code changes)

### Testing
```bash
# Launch app
python -m autonomiclab

# Test with sample Finapres dataset
# Navigate to: ~/Projects/Python/Finapres/Files/2025-09-10_09.04.59/
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: yaml` | `pip install pyyaml` |
| `ModuleNotFoundError: PyQt6` | `pip install PyQt6` |
| App won't start | Activate venv: `source venv/bin/activate` |
| Plots don't zoom | Check `fonts.yaml` exists in `autonomiclab/config/` |
| Fonts too small | Increase UI Zoom to 150-200% |
| Signals not loading | Ensure CSV files have correct prefix format |

---

## Performance Notes
- Typical dataset: 1422 seconds, 3 signals → instant load
- Zoom/pan is real-time (recalculates on each change)
- Memory: ~100MB for typical Finapres file
- No external dependencies beyond core requirements

---

## Next Steps
1. ✅ Deploy to clinician machines
2. ⏳ Add quantitative metrics (HRV, baroreflex gain)
3. ⏳ Export analysis results as PDF report
4. ⏳ Multi-dataset comparison
5. ⏳ Real-time data acquisition from device

---

## License
MIT License - See LICENSE file

## Contact
For questions: Contact developer or review main_window.py comments