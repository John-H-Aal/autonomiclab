# AutonomicLab — User Guide

## Starting the program

Double-click `AutonomicLab.exe` on your desktop.

**Windows SmartScreen warning:** The first time you run the installer or the program,
Windows may display a blue warning screen saying *"Windows protected your PC"*.
This is expected for software without a commercial code-signing certificate.

Click **More info**, then **Run anyway** to proceed.

A splash screen appears while the program loads.

---

## Loading a dataset

1. Click **Select Dataset** in the left panel
2. Navigate to a folder containing Finapres NOVA data files
3. The folder must contain a `*Markers.csv` file and the associated signal CSVs
4. Click **Select Folder**

The program automatically detects the datetime prefix and loads all signals.

---

## Analyses

### Valsalva Maneuver
Tests sympathetic and parasympathetic response to forced expiration against resistance.
- Shows: Blood Pressure (reBAP), Heart Rate (HR), Airway Pressure (PAirway)
- Phases: I, II (early/late), III, IV

### Stand Test
Tests orthostatic blood pressure regulation upon standing.
- Shows: Blood Pressure (reBAP), Heart Rate (HR)

### Deep Breathing
Tests parasympathetic function via respiratory sinus arrhythmia (RSA).
- Shows: Heart Rate (HR), Respiratory Wave

---

## Filtering by phase

Use the **Phase** dropdown in the left panel to switch between:
- **All** — shows full recording
- **Valsalva** — zooms to Valsalva segments
- **Stand Test** — zooms to Stand Test segments
- **Deep Breathing** — zooms to Deep Breathing segments

---

## Markers table

The left panel shows all markers from the recording with time (s), phase, and label.
Click a marker row to jump to that time point in the plot.

---

## Exporting results

Click **Export Excel** to save the analysis results as an `.xlsx` file.

---

## Zoom and navigation

Use the plot controls to zoom and pan the signal view.
UI font size can be adjusted with the zoom slider in the left panel.

---

## Data folder

The default data folder is set in `config.yaml` next to `AutonomicLab.exe`:

```yaml
data_folder: "C:/Users/YourName/Documents/AutonomicLab/data"
```

Place your Finapres dataset folders inside this folder — one subfolder per recording session.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No signals shown after loading | Check that CSV files have the correct datetime prefix format |
| Markers table is empty | Ensure a `*Markers.csv` file exists in the selected folder |
| Program loads slowly | Normal on first start — splash screen is shown during loading |
| Export fails | Ensure the data folder is writable |
