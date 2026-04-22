$WshShell = New-Object -ComObject WScript.Shell
$StartupPath = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup\AuraWhisper.lnk")
$Shortcut = $WshShell.CreateShortcut($StartupPath)
$Shortcut.TargetPath = "d:\Users\zod5532743\マイドライブ\Antigravity\AuraWhisper\autostart.vbs"
$Shortcut.WorkingDirectory = "d:\Users\zod5532743\マイドライブ\Antigravity\AuraWhisper"
$Shortcut.Save()
Write-Output "Shortcut created at $StartupPath"
