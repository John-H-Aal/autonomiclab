# Installing AutonomicLab on Windows 11

## Step 1 — Download the program

1. Go to: `https://github.com/John-H-Aal/autonomiclab/releases/latest`
2. Under **Assets**, download all three files:
   - `AutonomicLab.exe`
   - `config.yaml`
   - `autonomiclab_splash.png`
3. Place all three files in the same folder, for example:
   ```
   C:\Users\YourName\Documents\AutonomicLab\
   ```

> **Important:** All three files must be in the same folder.

---

## Step 2 — Allow the program to run

Windows may block the program the first time. Do one of the following:

**Option A — File properties:**
1. Right-click `AutonomicLab.exe` → **Properties**
2. At the bottom, check **Unblock** → click **OK**

**Option B — SmartScreen warning:**
If a blue warning appears when starting the program:
1. Click **More info**
2. Click **Run anyway**

---

## Step 3 — Configure data folder

Open `config.yaml` in Notepad and set the path to your data folder:

```yaml
data_folder: "C:/Users/YourName/Documents/data"
```

Save the file.

---

## Step 4 — Start the program

Double-click `AutonomicLab.exe`.

To create a desktop shortcut:
- Right-click `AutonomicLab.exe` → **Send to** → **Desktop (create shortcut)**

---

## Using the program

1. Click **Select Dataset** in the left panel
2. Navigate to a folder containing Finapres data files
3. Select the test type (Valsalva / Stand Test / Deep Breathing)
4. Use **Export Excel** to save results

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Program does not start | Make sure all 3 files are in the same folder |
| Data folder not found | Edit `config.yaml` with the correct path |
| Windows blocks the program | See Step 2 above |
| Plots are empty | Check that the Finapres CSV files are in the selected folder |
