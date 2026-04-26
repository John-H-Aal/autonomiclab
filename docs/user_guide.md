# AutonomicLab — User Guide

## Starting the program

Double-click `AutonomicLab.exe` on your desktop.

**Windows SmartScreen warning:** The first time you run the installer or the program,
Windows may display a blue warning screen saying *"Windows protected your PC"*.
This is expected for software without a commercial code-signing certificate.

Click **More info**, then **Run anyway** to proceed.

A splash screen appears while the program loads, followed by the login dialog.

---

## Logging in

When the program starts, a login dialog is shown.

- Enter your **username** and **password** and click **Log in**.
- If you do not have an account, click **Fortsæt som gæst** to launch as a guest.
  Guest access is limited to a fixed number of launches per machine.
  Contact your administrator to create a personal account.

If no user accounts have been created yet (first run), the login dialog is skipped
and you go directly to the main window.

---

## Loading a dataset

Click **Open Dataset** in the left panel. A file browser opens.

### CSV dataset (folder)

1. Navigate into the folder containing your Finapres data files using double-click.
2. The folder must contain a `*Markers.csv` file and the associated signal CSVs.
3. Click **Select This Folder** (bottom right of the dialog).

The program automatically detects the datetime prefix and loads all signals.

### Finapres NOVA recording (.nsc file)

1. Navigate to the `.nsc` file.
2. Single-click the file to select it.
3. Click **Open**.

> **Note:** `.nsc` files do not contain protocol markers, so the markers table will be empty
> and phase filtering is not available for this format.

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

Phase filtering is only available for CSV datasets that contain a markers file.

---

## Markers table

The left panel shows all markers from the recording with time (s), phase, and label.
Click a marker row to jump to that time point in the plot.

---

## Raw Data Viewer

Click **View Raw Data** to open the raw signal viewer for the loaded dataset.

The viewer shows individual waveforms and beat-by-beat signals on aligned time axes:

- **Blood pressure** — reBAP waveform
- **Heart rate** — HR AP and HR ECG (RR-interval)
- **Airway pressure** — PAirway
- **PTT** — Pulse Transit Time (shown when both HR AP and HR ECG are available)
- **ECG leads** — I, II, III, aVR, aVL, aVF, C1

Use the checkboxes in the left panel of the viewer to show or hide individual ECG leads.
Axes are linked: panning or zooming one plot moves all plots together.

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

## User accounts

AutonomicLab has three access levels:

| Role | Access |
|---|---|
| **Admin** | Full access, including the Admin panel (user management) |
| **Investigator** | Full access to all analyses and export |
| **Guest** | Full access, limited to a fixed number of launches per machine |

Administrators can add, remove, and reset user accounts via **Settings → Admin Panel**.

To create the first administrator account, run `scripts/create_admin.py` from the
command line on the machine where the program is installed.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| No signals shown after loading | Check that CSV files have the correct datetime prefix format |
| Markers table is empty | Ensure a `*Markers.csv` file exists in the selected folder, or note that .nsc files do not carry markers |
| "Select This Folder" is greyed out | The current folder contains no CSV files — navigate to the correct dataset folder |
| Program loads slowly | Normal on first start — splash screen is shown during loading |
| Export fails | Ensure the data folder is writable |
| Guest launches exhausted | Contact your administrator to create a personal account |
