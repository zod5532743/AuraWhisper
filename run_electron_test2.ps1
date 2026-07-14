$exe = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\aurawhisper.exe"
Copy-Item "d:\VSCODE\AuraWhisper\test_electron_minimal.js" "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\"
Write-Host "=== Launching Electron ==="
Start-Process -NoNewWindow -FilePath $exe -ArgumentList "test_electron_minimal.js", "--no-sandbox" -PassThru -RedirectStandardOutput "$env:TEMP\electron_stdout.txt" -RedirectStandardError "$env:TEMP\electron_stderr.txt" | Out-Null
Write-Host "Waiting..."
Start-Sleep 10
Write-Host "=== STDOUT ==="
Get-Content "$env:TEMP\electron_stdout.txt" -Tail 30
Write-Host "=== STDERR (last 10) ==="
Get-Content "$env:TEMP\electron_stderr.txt" -Tail 10
Write-Host "=== electon_test_result.txt ==="
Get-Content "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\electron_test_result.txt" -Tail 30
