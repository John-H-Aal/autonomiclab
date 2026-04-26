# Building AutonomicLab for Windows

## Recommended: Automated build via GitHub Actions

The easiest way to produce a new Windows release is to push a version tag.
GitHub builds the `.exe` automatically — no Windows machine needed.

### Steps

1. Commit and push all changes to `main`:
   ```bash
   git add .
   git commit -m "Release v1.x.x"
   git push
   ```

2. Create and push a version tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. GitHub Actions starts automatically. Go to:
   `https://github.com/John-H-Aal/autonomiclab/actions`
   to follow the build progress (~3–5 minutes).

4. When complete, the release is published at:
   `https://github.com/John-H-Aal/autonomiclab/releases`
   with two downloadable files:
   - `AutonomicLab_Setup_<version>.exe` — Inno Setup installer (bundles the EXE, splash, config template, and PDF user guide).
   - `UserGuide-<version>.pdf` — standalone copy of the user guide.

---

## Manual build (Windows 11)

Use this if you need to test locally before releasing.

### Requirements
- Windows 11
- Python 3.12 ([python.org](https://www.python.org/downloads/))
- Git ([git-scm.com](https://git-scm.com/download/win))

### Steps

```powershell
git clone https://github.com/John-H-Aal/autonomiclab.git
cd autonomiclab
venv\Scripts\activate
.\build.ps1
```

Output is in `dist\`:
```
dist\
  AutonomicLab.exe
  config.yaml
  autonomiclab_splash.png
```

---

## Updating assets (icon / splash screen)

Run on Linux/macOS (requires Pillow):

```bash
python create_assets.py
```

This regenerates:
- `assets/autonomiclab.ico`
- `assets/autonomiclab_splash.png`

Commit both files before tagging a release.

---

## Configuration

Edit `dist\config.yaml` before distributing to a customer:

```yaml
data_folder: "C:/Users/CUSTOMER_NAME/Documents/data"
```
