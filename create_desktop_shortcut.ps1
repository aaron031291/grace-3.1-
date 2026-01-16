# PowerShell script to create Grace desktop shortcut
# Run: powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherBat = Join-Path $scriptDir "launch_grace.bat"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Grace.lnk"

# Create WScript Shell object
$WScriptShell = New-Object -ComObject WScript.Shell

# Create shortcut
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherBat
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "Launch Grace - AI Knowledge System"
$shortcut.IconLocation = "C:\Windows\System32\shell32.dll,137"  # Folder icon

# Save shortcut
$shortcut.Save()

Write-Host "Desktop shortcut created: $shortcutPath" -ForegroundColor Green
Write-Host "  Target: $launcherBat" -ForegroundColor Gray
Write-Host "  Working Directory: $scriptDir" -ForegroundColor Gray
Write-Host ""
Write-Host "You can now double-click Grace on your desktop to launch!" -ForegroundColor Cyan
