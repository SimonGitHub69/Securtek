# Crea dist/Securtek-client-mac-vVERSION.zip (installer autoinstallante client Mac)
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$script = Join-Path $root "scripts\build-macos-client-installer.py"
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

if (Test-Path $venvPy) {
    $py = $venvPy
} else {
    $py = "python"
}

& $py $script
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
