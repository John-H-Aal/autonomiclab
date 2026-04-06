# Installing AutonomicLab on Windows 11

## Step 1 — Download the installer

Go to: `https://github.com/John-H-Aal/autonomiclab/releases/latest`

Click **AutonomicLab_Setup.exe** to download.

## Step 2 — Run the installer

1. Double-click `AutonomicLab_Setup.exe`
2. If Windows SmartScreen appears: click **More info** → **Run anyway**
3. Follow the setup wizard — click **Next** and **Install**
4. Optionally check **Create a desktop shortcut**
5. Click **Finish** — AutonomicLab starts automatically

## Step 3 — Place your data files

The installer creates this folder automatically:
```
C:\Users\YourName\Documents\AutonomicLab\data\
```
Copy your Finapres dataset folders here.

## Step 4 — Configure data path (if needed)

If your data is stored elsewhere, open `config.yaml` in the installation folder
and change the `data_folder` path:

```
C:\Users\YourName\AppData\Local\AutonomicLab\config.yaml
```

## Uninstalling

**Settings** → **Apps** → search for *AutonomicLab* → **Uninstall**
