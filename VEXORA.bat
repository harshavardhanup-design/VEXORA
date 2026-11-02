@echo off
cd /d "%~dp0"
if exist "%~dp0dist\VEXORA\VEXORA.exe" (
    start "" "%~dp0dist\VEXORA\VEXORA.exe"
    exit /b 0
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
    exit /b 0
)
if exist "C:\Users\ASUS\.gemini\antigravity\scratch\VEXORA\.venv\Scripts\pythonw.exe" (
    start "" "C:\Users\ASUS\.gemini\antigravity\scratch\VEXORA\.venv\Scripts\pythonw.exe" "%~dp0main.py"
    exit /b 0
)
start "" pythonw "%~dp0main.py"
