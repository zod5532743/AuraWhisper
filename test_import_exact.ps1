# main.js の import チェックを完全に再現
$pythonExe = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\backend\venv\Scripts\python.exe"
$cwd = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\backend"

Write-Host "Python: $pythonExe"
Write-Host "CWD: $cwd"
Write-Host ""

# --- main.js の import チェックを完全再現 ---
# execSync(`"${pythonExe}" -c "import fastapi, uvicorn, faster_whisper, sounddevice"`);
Write-Host "--- Test: import check (like main.js) ---"
$cmd = "`"$pythonExe`" -c `"import fastapi, uvicorn, faster_whisper, sounddevice; print('IMPORT OK')`""
Write-Host "Command: $cmd"

try {
    $output = & cmd.exe /c $cmd 2>&1
    $exitCode = $LASTEXITCODE
    Write-Host "ExitCode: $exitCode"
    Write-Host "Output: $output"
    if ($exitCode -eq 0) {
        Write-Host "IMPORT CHECK PASSED"
    } else {
        Write-Host "IMPORT CHECK FAILED"
    }
}
catch {
    Write-Host "EXCEPTION: $_"
}
Write-Host ""

# --- spawn に渡す引数で直接起動 ---
Write-Host "--- Test: spawn equivalent (server.py) ---"
Write-Host "Starting server.py directly..."
$p = Start-Process -NoNewWindow -FilePath $pythonExe -ArgumentList "server.py" -WorkingDirectory $cwd -PassThru -RedirectStandardError "$env:TEMP\server_test_stderr.txt"
Start-Sleep 4
Write-Host "Server PID: $($p.Id)"
Write-Host "Server running: $(-not $p.HasExited)"
$p.Kill()
Write-Host "=== STDERR (first 30 lines) ==="
Get-Content "$env:TEMP\server_test_stderr.txt" -TotalCount 30
