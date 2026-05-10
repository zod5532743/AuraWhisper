# Define variables for paths
$buildDir = "d:\temp_aurawhisper_release"
$currentDir = $PSScriptRoot
$distDir = Join-Path -Path $currentDir -ChildPath "dist"
$zipFileName = "AuraWhisper_v1.2.5.zip"

# Ensure the build directory exists
if (-Not (Test-Path -Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir
}

# Run npm run package in the current directory
Set-Location -Path $currentDir
npm run package

# Get the built setup executable or win-unpacked folder from dist directory
$setupFile = Get-ChildItem -Path $distDir -Filter "AuraWhisper*Setup*.exe" | Select-Object -First 1
$winUnpackedFolder = Join-Path -Path $distDir -ChildPath "win-unpacked"

# Compress the setup executable or win-unpacked folder into a zip file
if ($setupFile) {
    Compress-Archive -Path $setupFile.FullName -DestinationPath (Join-Path -Path $buildDir -ChildPath $zipFileName) -Force
} elseif (Test-Path -Path $winUnpackedFolder) {
    Compress-Archive -Path $winUnpackedFolder -DestinationPath (Join-Path -Path $buildDir -ChildPath $zipFileName) -Force
}

# Copy the newly created zip file back into dist directory
Copy-Item -Path (Join-Path -Path $buildDir -ChildPath $zipFileName) -Destination $distDir -Force

Write-Output "Build and packaging completed successfully. Zip file is at $distDir\$zipFileName"
