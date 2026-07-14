$exe = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\aurawhisper.exe"
$script = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\test_execsync.js"
Write-Host "Launching Electron with test script..."
$p = Start-Process -NoNewWindow -FilePath $exe -ArgumentList $script, "--no-sandbox" -PassThru -RedirectStandardOutput "$env:TEMP\electron_test.txt" -RedirectStandardError "$env:TEMP\electron_test_err.txt"
$r = $p.WaitForExit(30000)
Write-Host "ExitCode: $($p.ExitCode)"
Write-Host "=== STDOUT ==="
Get-Content "$env:TEMP\electron_test.txt"
Write-Host "=== STDERR (tail 50) ==="
Get-Content "$env:TEMP\electron_test_err.txt" -Tail 50
