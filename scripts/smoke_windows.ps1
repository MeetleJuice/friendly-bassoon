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
