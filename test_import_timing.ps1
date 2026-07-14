$venvPy = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\backend\venv\Scripts\python.exe"
$script = "C:\Users\zod5532743\AppData\Local\Programs\aurawhisper\resources\app\backend\test_import_hang.py"
Write-Host "Starting Python import test..."
$p = Start-Process -NoNewWindow -FilePath $venvPy -ArgumentList $script -PassThru -RedirectStandardOutput "$env:TEMP\import_test.txt" -RedirectStandardError "$env:TEMP\import_test_err.txt"
$completed = $p.WaitForExit(120000)
if (!$completed) {
    Write-Host "TIMEOUT - Process HUNG for 120s, killing..."
    $p.Kill()
} else {
    Write-Host "Process exited with code $($p.ExitCode)"
}
Write-Host "=== STDOUT ==="
Get-Content "$env:TEMP\import_test.txt" -ErrorAction SilentlyContinue
Write-Host "=== STDERR ==="
Get-Content "$env:TEMP\import_test_err.txt" -ErrorAction SilentlyContinue
