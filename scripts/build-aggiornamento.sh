#!/usr/bin/env bash
# Crea dist/securtek-<VERSION>-aggiornamento e zip Securtek-aggiornamento-v<VERSION>.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$ROOT/VERSION"

if [[ ! -f "$VERSION_FILE" ]]; then
    echo "File VERSION non trovato in $ROOT" >&2
    exit 1
fi

VERSION="$(tr -d '[:space:]' < "$VERSION_FILE")"
DEST="$ROOT/dist/securtek-${VERSION}-aggiornamento"
ZIP_PATH="$ROOT/dist/Securtek-aggiornamento-v${VERSION}.zip"

PATHS=(
    VERSION
    apps/core/context_processors.py
    apps/core/middleware.py
    apps/pratiche/forms.py
    apps/pratiche/urls.py
    apps/pratiche/views.py
    apps/pratiche/services/desktop_helper_client.py
    apps/pratiche/services/desktop_open.py
    apps/pratiche/services/folder_picker.py
    apps/pratiche/templates/pratiche/folder_picker_popup.html
    apps/pratiche/templates/pratiche/pratica_form.html
    apps/pratiche/templates/pratiche/pratica_categoria_form.html
    apps/dashboard/views.py
    config/__init__.py
    config/admin.py
    config/apps.py
    config/settings.py
    config/urls.py
    config/version.py
    config/views.py
    docs/README.md
    scripts/securtek_desktop_helper.py
    scripts/win_pick_folder.py
    scripts/win_pick_folder.ps1
    scripts/build-aggiornamento.sh
    scripts/BuildAggiornamento.command
    scripts/build-aggiornamento.bat
    scripts/build-aggiornamento.ps1
    static/securtek/css/admin-password-toggle.css
    static/securtek/css/multi-window.css
    static/securtek/css/navbar.css
    static/securtek/js/admin-password-toggle.js
    static/securtek/js/desktop-folder.js
    static/securtek/js/desktop-open.js
    static/securtek/js/disable-autocomplete.js
    static/securtek/js/embed.js
    static/securtek/js/multi-window.js
    templates/admin/base_site.html
    templates/admin/login.html
    templates/base/footer.html
    templates/base/layout.html
    templates/base/navbar.html
)

SUBDIRS=(
    deploy/macos
    deploy/macos-client
    deploy/windows
)

rm -rf "$DEST"
mkdir -p "$DEST"

for rel in "${PATHS[@]}"; do
    src="$ROOT/$rel"
    if [[ ! -f "$src" ]]; then
        echo "File mancante: $rel" >&2
        exit 1
    fi
    out="$DEST/$rel"
    mkdir -p "$(dirname "$out")"
    cp "$src" "$out"
done

for sub in "${SUBDIRS[@]}"; do
    cp -R "$ROOT/$sub" "$DEST/$(dirname "$sub")/"
done

cat > "$DEST/INSTALLAZIONE.txt" <<EOF
Securtek - aggiornamento v. ${VERSION}
==================================

File zip: Securtek-aggiornamento-v${VERSION}.zip
Dopo estrazione (macOS): cartella Securtek-aggiornamento-v${VERSION}

## 1. Mac Mini (SERVER)

1. Backup di ~/Progetti/Securtek (consigliato).
2. Copia il contenuto della cartella estratta sopra ~/Progetti/Securtek:

   cp -R ~/Downloads/Securtek-aggiornamento-v${VERSION}/* ~/Progetti/Securtek/

3. Terminale:

   cd ~/Progetti/Securtek
   .venv/bin/python manage.py collectstatic --noinput
   sudo launchctl kickstart -k system/com.securtek.gunicorn

4. Verifica:

   curl http://127.0.0.1:8000/version/

   Deve rispondere: "version": "${VERSION}"

## 2. Login (staff / app)

Dopo il riavvio Gunicorn, su ciascun utente Django:

- Staff spento + Attivo = entra nell'app
- Staff acceso = entra nel menu Django

Sui client (Windows / iMac) basta riaprire Securtek e Ctrl+F5.
Non serve reinstallare l'app Desktop per questo aggiornamento.

## 3. Mac client (iMac) — solo se serve anche l'helper cartelle

1. Copia deploy/macos-client/ sul Mac client.
2. Terminale:

   cd ~/Downloads/macos-client
   bash install-client.sh

3. Verifica helper:

   curl http://127.0.0.1:18765/health

   "version": 3

4. Ricarica Securtek con Cmd+Shift+R.

## Note

- Sul Mini NON serve git pull se copi questo zip.
- Se l'anteprima fallisce, controlla che i popup siano consentiti per Securtek.
EOF

rm -f "$ZIP_PATH"
mkdir -p "$(dirname "$ZIP_PATH")"
( cd "$DEST" && zip -r -q "$ZIP_PATH" . )

echo "Pacchetto: $DEST"
echo "Zip:       $ZIP_PATH"
