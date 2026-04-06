# AutonomicLab build script
# Run from project root with: .\build.ps1

venv\Scripts\activate

pyinstaller --clean --onefile --windowed --name AutonomicLab `
  --icon "assets/autonomiclab.ico" `
  --splash "assets/autonomiclab_splash.png" `
  --add-data "autonomiclab/config/fonts.yaml;autonomiclab/config" `
  autonomiclab/__main__.py

# Copy assets to dist\
Copy-Item "assets\autonomiclab_splash.png" "dist\autonomiclab_splash.png"

# Copy config.yaml to dist\
if (Test-Path "config.yaml") {
    Copy-Item "config.yaml" "dist\config.yaml"
} else {
    @"
# AutonomicLab configuration
# Place this file in the same folder as AutonomicLab.exe

data_folder: "C:/Users/johnh/Documents/data"
"@ | Out-File -FilePath "dist\config.yaml" -Encoding utf8
}

Write-Host ""
Write-Host "Build complete! Files in dist\"
Write-Host "  AutonomicLab.exe"
Write-Host "  config.yaml"
