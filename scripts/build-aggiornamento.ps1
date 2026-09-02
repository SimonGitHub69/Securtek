# Crea pacchetto dist/securtek-<VERSION>-aggiornamento e zip Securtek-aggiornamento-v<VERSION>.zip
$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$versionFile = Join-Path $root "VERSION"
if (-not (Test-Path $versionFile)) {
    Write-Error "File VERSION non trovato in $root"
}
$version = (Get-Content $versionFile -Raw).Trim()
$dest = Join-Path $root "dist\securtek-$version-aggiornamento"
$zipPath = Join-Path $root "dist\Securtek-aggiornamento-v$version.zip"

if (Test-Path $dest) {
    Remove-Item -Recurse -Force $dest
}
New-Item -ItemType Directory -Path $dest -Force | Out-Null

$paths = @(
    "VERSION",
    "apps\core\context_processors.py",
    "apps\core\middleware.py",
    "apps\pratiche\forms.py",
    "apps\pratiche\urls.py",
    "apps\pratiche\views.py",
    "apps\pratiche\services\desktop_helper_client.py",
    "apps\pratiche\services\desktop_open.py",
    "apps\pratiche\services\folder_picker.py",
    "apps\pratiche\templates\pratiche\folder_picker_popup.html",
    "apps\pratiche\templates\pratiche\pratica_form.html",
    "apps\pratiche\templates\pratiche\pratica_categoria_form.html",
    "config\settings.py",
    "config\urls.py",
    "config\version.py",
    "config\views.py",
    "docs\README.md",
    "scripts\securtek_desktop_helper.py",
    "scripts\win_pick_folder.py",
    "scripts\win_pick_folder.ps1",
    "scripts\build-aggiornamento.sh",
    "scripts\BuildAggiornamento.command",
    "scripts\build-aggiornamento.bat",
    "scripts\build-aggiornamento.ps1",
    "static\securtek\css\admin-password-toggle.css",
    "static\securtek\css\multi-window.css",
    "static\securtek\css\navbar.css",
    "static\securtek\js\admin-password-toggle.js",
    "static\securtek\js\desktop-folder.js",
    "static\securtek\js\desktop-open.js",
    "static\securtek\js\disable-autocomplete.js",
    "static\securtek\js\embed.js",
    "static\securtek\js\multi-window.js",
    "templates\admin\base_site.html",
    "templates\admin\login.html",
    "templates\base\footer.html",
    "templates\base\layout.html",
    "templates\base\navbar.html"
)

foreach ($rel in $paths) {
    $src = Join-Path $root $rel
    if (-not (Test-Path $src)) {
        Write-Error "File mancante: $rel"
    }
    $out = Join-Path $dest $rel
    $outDir = Split-Path $out -Parent
    if (-not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
    Copy-Item -Path $src -Destination $out -Force
}

foreach ($subdir in @("deploy\macos", "deploy\macos-client", "deploy\windows")) {
    $srcDir = Join-Path $root $subdir
    $outDir = Join-Path $dest $subdir
    Copy-Item -Path $srcDir -Destination $outDir -Recurse -Force
}

$installazione = @"
Securtek - aggiornamento v. $version
==================================

File zip: Securtek-aggiornamento-v$version.zip
Dopo estrazione (macOS): cartella Securtek-aggiornamento-v$version

## 1. Mac Mini (SERVER)

1. Backup di ~/Progetti/Securtek (consigliato).
2. Copia il contenuto della cartella estratta sopra ~/Progetti/Securtek:

   cp -R ~/Downloads/Securtek-aggiornamento-v$version/* ~/Progetti/Securtek/

3. Terminale:

   cd ~/Progetti/Securtek
   .venv/bin/python manage.py collectstatic --noinput
   sudo launchctl kickstart -k system/com.securtek.gunicorn

4. Verifica:

   curl http://127.0.0.1:8000/version/

   Deve rispondere: "version": "$version"

## 2. Mac client (iMac)

1. Copia deploy/macos-client/ sul Mac client.
2. Terminale:

   cd ~/Downloads/macos-client
   bash install-client.sh

3. Verifica helper:

   curl http://127.0.0.1:18765/health

   "version": 3

4. Ricarica Securtek con Ctrl+F5.

## Note

- Sul Mini NON serve git pull se copi questo zip.
- Se l'anteprima fallisce, controlla che i popup siano consentiti per Securtek.
"@
$installPath = Join-Path $dest "INSTALLAZIONE.txt"
[System.IO.File]::WriteAllText($installPath, $installazione, (New-Object System.Text.UTF8Encoding $false))

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path "$dest\*" -DestinationPath $zipPath -Force

Write-Host "Pacchetto: $dest"
Write-Host "Zip:       $zipPath"
