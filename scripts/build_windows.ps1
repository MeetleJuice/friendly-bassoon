# Execute from a Windows PowerShell terminal in the repository. CI uses the same script.
param([string]$Version = "")
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
if (-not $Version) {
    $Version = (& python -c "from aigentics import __version__; print(__version__)").Trim()
    if ($LASTEXITCODE -ne 0) { throw "Could not determine application version" }
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Invalid release version" }
& python scripts/make_icon.py
if ($LASTEXITCODE -ne 0) { throw "Icon rendering failed" }
& python -m PyInstaller --noconfirm --clean packaging/Aigentics.spec
if ($LASTEXITCODE -ne 0) { throw "Executable build failed" }
$isccPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $isccPath)) {
    throw "Install Inno Setup 6 from https://jrsoftware.org/isdl.php, then run this build again."
}
& $isccPath "/DAppVersion=$Version" packaging/installer.iss
if ($LASTEXITCODE -ne 0) { throw "Installer compilation failed" }
$installerPath = Join-Path $repoRoot "dist/installer/Aigentics-Setup-$Version.exe"
if (-not (Test-Path $installerPath)) { throw "Expected installer is missing" }
$checksum = (Get-FileHash $installerPath -Algorithm SHA256).Hash.ToLowerInvariant()
$checksumPath = Join-Path $repoRoot "dist/installer/SHA256SUMS.txt"
[System.IO.File]::WriteAllText($checksumPath, "$checksum  Aigentics-Setup-$Version.exe`n", [System.Text.UTF8Encoding]::new($false))
Write-Output "Installer and checksum created in dist/installer"
