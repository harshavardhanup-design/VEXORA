# Creates a native Windows 11 Desktop Shortcut for compiled VEXORA.exe
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$TargetFolder = "C:\Users\ASUS\OneDrive\Desktop\VEXORA_v5_8_1_PROFESSIONAL_AI_AGENT\dist\VEXORA"
$TargetExe = Join-Path $TargetFolder "VEXORA.exe"

if (-not (Test-Path $TargetExe)) {
    $TargetFolder = Join-Path (Get-Location).Path "dist\VEXORA"
    $TargetExe = Join-Path $TargetFolder "VEXORA.exe"
}

$ShortcutPath = Join-Path $DesktopPath "VEXORA.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetExe
$Shortcut.WorkingDirectory = $TargetFolder
$Shortcut.Description = "VEXORA - Snapdragon Copilot+ Desktop AI Assistant"
$Shortcut.Save()

Write-Host "Desktop Shortcut updated successfully at: $ShortcutPath"
Write-Host "Target: $TargetExe"
