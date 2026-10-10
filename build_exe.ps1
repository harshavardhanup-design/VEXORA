# ==============================================================================
# VEXORA — Standalone Windows 11 Executable Builder
# Snapdragon® AI Lab Build & Present Challenge Edition
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Building VEXORA Standalone Windows 11 Application" -ForegroundColor Cyan
Write-Host " Optimized for Snapdragon-Powered HP Copilot+ PCs" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Python environment
$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python.exe"
}

Write-Host "`n[1/3] Verifying PyInstaller..." -ForegroundColor Yellow
& $PythonExe -m pip install pyinstaller --quiet

Write-Host "`n[2/3] Compiling VEXORA Executable (PyInstaller)..." -ForegroundColor Yellow
& $PythonExe -m PyInstaller `
  --noconsole `
  --onedir `
  --name "VEXORA" `
  --clean `
  --add-data "app;app" `
  --add-data "core;core" `
  --add-data "ai;ai" `
  --add-data "tools;tools" `
  --add-data "monitoring;monitoring" `
  --add-data "memory;memory" `
  --add-data "security;security" `
  main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[3/3] Build Successful!" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " Executable location: .\dist\VEXORA\VEXORA.exe" -ForegroundColor Green
    Write-Host " Double-click VEXORA.exe to launch without requiring Python." -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host "`n[!] Build encountered an error. Check logs above." -ForegroundColor Red
}
