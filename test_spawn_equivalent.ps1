$py = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\backend\venv\Scripts\python.exe"
$cwd = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\backend"

Write-Host "=== Test 1: Direct python import ==="
$p = Start-Process -NoNewWindow -FilePath $py -ArgumentList "-c", "import fastapi, uvicorn, faster_whisper, sounddevice; print('IMPORT OK')" -WorkingDirectory $cwd -PassThru -RedirectStandardOutput "$env:TEMP\spawn_test_out.txt" -RedirectStandardError "$env:TEMP\spawn_test_err.txt"
$r = $p.WaitForExit(30000)
if ($r) {
    Write-Host "Exit code: $($p.ExitCode)"
    Write-Host "STDOUT: $(Get-Content $env:TEMP\spawn_test_out.txt)"
} else {
    Write-Host "TIMEOUT - killing"
    $p.Kill()
}

Write-Host "=== Test 2: spawn server.py (5s) ==="
$p2 = Start-Process -NoNewWindow -FilePath $py -ArgumentList "server.py" -WorkingDirectory $cwd -PassThru -RedirectStandardOutput "$env:TEMP\spawn_srv_out.txt" -RedirectStandardError "$env:TEMP\spawn_srv_err.txt"
Start-Sleep -Seconds 5
if (!$p2.HasExited) {
    Write-Host "Server running after 5s - OK"
    $p2.Kill()
} else {
    Write-Host "Server exited with code $($p2.ExitCode)"
}
Write-Host "STDERR:"
Get-Content $env:TEMP\spawn_srv_err.txt -Head 30
