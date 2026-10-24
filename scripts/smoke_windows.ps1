# Install the actual wizard output silently in a disposable directory, inspect shortcuts and run its exe.
param([Parameter(Mandatory=$true)][string]$Version)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$temporaryRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$installRoot = Join-Path $temporaryRoot "aigentics-installed-smoke"
$installerPath = Join-Path $repoRoot "dist/installer/Aigentics-Setup-$Version.exe"
$setupLog = Join-Path (Split-Path $installRoot) "aigentics-setup.log"
$process = Start-Process -FilePath $installerPath -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS=desktopicon', "/DIR=`"$installRoot`"", "/LOG=`"$setupLog`"") -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Installer smoke failed: exit $($process.ExitCode)" }
$executablePath = Join-Path $installRoot "Aigentics.exe"
if (-not (Test-Path $executablePath)) { throw "Installed executable not found" }
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Aigentics Desktop.lnk'
if (-not (Test-Path $shortcutPath)) { throw "Desktop shortcut not created" }
$shellObject = New-Object -ComObject WScript.Shell
$shortcut = $shellObject.CreateShortcut($shortcutPath)
if ($shortcut.TargetPath -ne $executablePath) { throw "Desktop shortcut has incorrect target" }
$env:AIGENTICS_DATA_DIR = Join-Path $installRoot 'smoke-data'
$env:QT_QPA_PLATFORM = 'offscreen'
$app = Start-Process -FilePath $executablePath -ArgumentList '--smoke-test' -PassThru
if (-not $app.WaitForExit(60000)) { $app.Kill(); throw "Installed app startup timed out" }
if ($app.ExitCode -ne 0) { throw "Installed app startup failed: exit $($app.ExitCode)" }
if (-not (Test-Path (Join-Path $env:AIGENTICS_DATA_DIR 'aigentics.sqlite3'))) { throw "Installed app did not initialize SQLite" }
# The smoke created this shortcut in the runner's disposable desktop; remove it.
Remove-Item $shortcutPath
Write-Output "Windows installer, desktop shortcut, packaged GUI, SQLite and shutdown smoke passed."

# Exercise the shipped diagnostic runner without pytest, Ollama, secrets or GitHub submission.
$diagnostics = Start-Process -FilePath $executablePath -ArgumentList '--diagnostic-smoke-test' -PassThru
if (-not $diagnostics.WaitForExit(60000)) { $diagnostics.Kill(); throw "Packaged diagnostic suite timed out" }
if ($diagnostics.ExitCode -ne 0) { throw "Packaged diagnostic suite failed: exit $($diagnostics.ExitCode)" }
Write-Output "All 23 built-in packaged diagnostic checks passed. No support report was submitted."

# Verify migration from the public 0.10.0 installer, using its previously verified immutable checksum.
$previousInstaller = Join-Path $temporaryRoot 'Aigentics-Setup-0.10.0.exe'
Invoke-WebRequest -Uri 'https://github.com/MeetleJuice/friendly-bassoon/releases/download/v0.10.0/Aigentics-Setup-0.10.0.exe' -OutFile $previousInstaller
$expectedPreviousHash = '81681a21b42e3623a19cff80e4e54410d26f48fb7603b6b450c8c3a4f69788ba'
if ((Get-FileHash $previousInstaller -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedPreviousHash) {
    throw 'Previous release failed its pinned checksum; refusing upgrade test'
}
$upgradeRoot = Join-Path $temporaryRoot 'aigentics-upgrade-install'
$env:AIGENTICS_DATA_DIR = Join-Path $temporaryRoot 'aigentics-upgrade-data'
$oldSetup = Start-Process -FilePath $previousInstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$upgradeRoot`"") -Wait -PassThru
if ($oldSetup.ExitCode -ne 0) { throw 'Previous installer failed' }
$upgradeExe = Join-Path $upgradeRoot 'Aigentics.exe'
$oldApp = Start-Process -FilePath $upgradeExe -ArgumentList '--smoke-test' -PassThru
if (-not $oldApp.WaitForExit(60000)) { $oldApp.Kill(); throw 'Previous app startup timed out' }
if ($oldApp.ExitCode -ne 0) { throw 'Previous app startup failed' }
python scripts/upgrade_probe.py seed $env:AIGENTICS_DATA_DIR
if ($LASTEXITCODE -ne 0) { throw 'Could not seed previous-release fixture' }
$newSetup = Start-Process -FilePath $installerPath -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$upgradeRoot`"") -Wait -PassThru
if ($newSetup.ExitCode -ne 0) { throw 'Upgrade installer failed' }
$newApp = Start-Process -FilePath $upgradeExe -ArgumentList '--smoke-test' -PassThru
if (-not $newApp.WaitForExit(60000)) { $newApp.Kill(); throw 'Upgraded app startup timed out' }
if ($newApp.ExitCode -ne 0) { throw 'Upgraded app startup failed' }
python scripts/upgrade_probe.py verify $env:AIGENTICS_DATA_DIR
if ($LASTEXITCODE -ne 0) { throw 'Upgrade did not preserve data' }
if (Test-Path $shortcutPath) { Remove-Item $shortcutPath }
Write-Output 'Real 0.10.0-to-current upgrade preserved agents, settings and session history; schema and project/assessment preservation passed.'
