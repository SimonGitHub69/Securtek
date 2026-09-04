# Crea pacchetto dist/securtek-<VERSION>-aggiornamento e zip Securtek-aggiornamento-v<VERSION>.zip
# Pacchetto completo di allineamento (non solo delta dell'ultima feature).
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
    # Agenda / notifiche mail
    "apps\agenda\admin.py",
    "apps\agenda\forms.py",
    "apps\agenda\management\commands\invia_notifiche_agenda.py",
    "apps\agenda\migrations\0006_lognotificaemail_ora_invio.py",
    "apps\agenda\migrations\0007_configurazione_servizio_intervallo.py",
    "apps\agenda\migrations\0008_configurazione_template_mail.py",
    "apps\agenda\models.py",
    "apps\agenda\services\notifiche.py",
    "apps\agenda\services\servizio_notifiche.py",
    "apps\agenda\templates\agenda\agenda_calendar.html",
    "apps\agenda\templates\agenda\agenda_day.html",
    "apps\agenda\templates\agenda\configurazione_email_form.html",
    "apps\agenda\templates\agenda\evento_form.html",
    "apps\agenda\templates\agenda\log_notifiche_email_list.html",
    "apps\agenda\urls.py",
    "apps\agenda\views.py",
    # Anagrafiche
    "apps\anagrafiche\forms\anagrafica.py",
    "apps\anagrafiche\forms\contatto.py",
    "apps\anagrafiche\forms\indirizzo.py",
    "apps\anagrafiche\templates\anagrafiche\anagrafica_detail.html",
    "apps\anagrafiche\templates\anagrafiche\anagrafica_form.html",
    "apps\anagrafiche\templates\anagrafiche\personale_form.html",
    "apps\anagrafiche\views\anagrafica.py",
    "apps\anagrafiche\views\personale.py",
    # Core / dashboard
    "apps\core\context_processors.py",
    "apps\core\middleware.py",
    "apps\dashboard\views.py",
    # Pratiche
    "apps\pratiche\forms.py",
    "apps\pratiche\models.py",
    "apps\pratiche\migrations\0023_templatepratica_tipologia_onetoone.py",
    "apps\pratiche\urls.py",
    "apps\pratiche\views.py",
    "apps\pratiche\services\desktop_helper_client.py",
    "apps\pratiche\services\desktop_open.py",
    "apps\pratiche\services\folder_picker.py",
    "apps\pratiche\templates\pratiche\comunicazione_preview.html",
    "apps\pratiche\templates\pratiche\folder_picker_popup.html",
    "apps\pratiche\templates\pratiche\pratica_categoria_form.html",
    "apps\pratiche\templates\pratiche\pratica_detail.html",
    "apps\pratiche\templates\pratiche\pratica_form.html",
    "apps\pratiche\templates\pratiche\_pratica_categorie_edit.html",
    "apps\pratiche\templates\pratiche\tecnico_form.html",
    # Config
    "config\__init__.py",
    "config\admin.py",
    "config\apps.py",
    "config\settings.py",
    "config\urls.py",
    "config\version.py",
    "config\views.py",
    "docs\README.md",
    # Scripts
    "scripts\securtek_desktop_helper.py",
    "scripts\win_pick_folder.py",
    "scripts\win_pick_folder.ps1",
    "scripts\build-aggiornamento.sh",
    "scripts\BuildAggiornamento.command",
    "scripts\build-aggiornamento.bat",
    "scripts\build-aggiornamento.ps1",
    # Static
    "static\securtek\css\admin-password-toggle.css",
    "static\securtek\css\multi-window.css",
    "static\securtek\css\navbar.css",
    "static\securtek\css\scroll-hold.css",
    "static\securtek\css\style.css",
    "static\securtek\js\admin-password-toggle.js",
    "static\securtek\js\app.js",
    "static\securtek\js\desktop-folder.js",
    "static\securtek\js\desktop-open.js",
    "static\securtek\js\disable-autocomplete.js",
    "static\securtek\js\embed.js",
    "static\securtek\js\multi-window.js",
    "static\securtek\js\scroll-hold.js",
    # Templates base
    "templates\admin\base_site.html",
    "templates\admin\login.html",
    "templates\base\footer.html",
    "templates\base\layout.html",
    "templates\base\navbar.html",
    "templates\base\sidebar.html"
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
Securtek - aggiornamento COMPLETO v. $version
=============================================

File zip: Securtek-aggiornamento-v$version.zip
Dopo estrazione (macOS): cartella Securtek-aggiornamento-v$version

Questo pacchetto allinea Mac Mini alla versione di sviluppo Windows
(include pratiche/agenda/anagrafiche, UI maschere, icone azione,
notifiche mail agenda, desktop helper, scroll, ecc.).

Novita principali v0.2.20:
- Parametri mail: modello oggetto e testo mail con segnaposto ({{titolo}}, {{data}}, …)
- Azzera Registro Mail; anagrafica contatti/indirizzi; SMTP robusto; servizio/intervallo
- Migrazioni agenda 0008 + pratiche 0023
- Su Mac Mini: migrate + collectstatic + riavvio gunicorn (Ctrl+F5)

## 1. Mac Mini (SERVER)

1. Backup di ~/Progetti/Securtek (consigliato).
2. Copia il contenuto della cartella estratta sopra ~/Progetti/Securtek:

   cp -R ~/Downloads/Securtek-aggiornamento-v$version/* ~/Progetti/Securtek/

3. Terminale:

   cd ~/Progetti/Securtek
   .venv/bin/python manage.py migrate
   .venv/bin/python manage.py collectstatic --noinput
   sudo launchctl kickstart -k system/com.securtek.gunicorn

4. Notifiche mail agenda (consigliato):

   chmod +x deploy/macos/run-agenda-notifiche.sh deploy/macos/install-agenda-notifiche.sh
   sudo ./deploy/macos/install-agenda-notifiche.sh --daemon

5. Verifica:

   curl http://127.0.0.1:8000/version/

   Deve rispondere: "version": "$version"

## 2. Login (staff / app)

Dopo il riavvio Gunicorn, su ciascun utente Django:

- Staff spento + Attivo = entra nell'app
- Staff acceso = entra nel menu Django

Sui client (Windows / iMac) basta riaprire Securtek e Ctrl+F5.

## 3. Mac client (iMac) — solo se serve anche l'helper cartelle

1. Copia deploy/macos-client/ sul Mac client.
2. Terminale:

   cd ~/Downloads/macos-client
   bash install-client.sh

3. Verifica helper:

   curl http://127.0.0.1:18765/health

4. Ricarica Securtek con Ctrl+F5.

## Note

- Sul Mini NON serve git pull se copi questo zip.
- Dopo l'aggiornamento fai Ctrl+F5 sui client browser.
"@
$installPath = Join-Path $dest "INSTALLAZIONE.txt"
[System.IO.File]::WriteAllText($installPath, $installazione, (New-Object System.Text.UTF8Encoding $false))

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

# Zip macOS-friendly: cartella root + path con /
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$folderName = "Securtek-aggiornamento-v$version"
$zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem $dest -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($dest.Length).TrimStart('\', '/') -replace '\\', '/'
        $entryName = "$folderName/$rel"
        [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $_.FullName,
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        )
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Pacchetto: $dest"
Write-Host "Zip:       $zipPath"
$fileCount = (Get-ChildItem $dest -Recurse -File | Measure-Object).Count
Write-Host "File:      $fileCount"
$zipSize = (Get-Item $zipPath).Length
Write-Host ("Size:      {0:N0} bytes" -f $zipSize)
