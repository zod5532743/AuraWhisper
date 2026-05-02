# Define source and destination paths
$sourceBackendFolder = ".\backend"
$distFolderPath = "D:\Users\zod5532743\マイドライブ\Antigravity\AuraWhisper\dist"
$winUnpackedPath = "$distFolderPath\win-unpacked\backend"

# Ensure the backend source exists
if (-Not (Test-Path -Path $sourceBackendFolder)) {
    Write-Error "Backend source folder not found at $sourceBackendFolder"
    exit
}

# Create the dist folder if it doesn't exist
if (-Not (Test-Path -Path $distFolderPath)) {
    New-Item -ItemType Directory -Force -Path $distFolderPath
}

# Cleanup existing win-unpacked backend if any
if (Test-Path -Path $winUnpackedPath) {
    Remove-Item -Recurse -Force $winUnpackedPath
}

# Create the win-unpacked\backend folder
New-Item -ItemType Directory -Force -Path $winUnpackedPath

# Copy backend folder to win-unpacked for immediate testing (excluding __pycache__)
Get-ChildItem -Path $sourceBackendFolder -Exclude "__pycache__" | Copy-Item -Destination $winUnpackedPath -Recurse -Force

# Create ZIP files for GitHub release
$zipFiles = @(
    "$distFolderPath\backend_cpu.zip",
    "$distFolderPath\backend_cuda.zip",
    "$distFolderPath\backend_dml.zip"
)

foreach ($zipFile in $zipFiles) {
    if (Test-Path -Path $zipFile) {
        Remove-Item -Force $zipFile
    }
    Compress-Archive -Path $sourceBackendFolder -DestinationPath $zipFile -Force
}

Write-Output "Preparation completed successfully."
Write-Output "1. Backend copied to $winUnpackedPath for local testing."
Write-Output "2. Release zips (cpu/cuda/dml) created in $distFolderPath for GitHub upload."
