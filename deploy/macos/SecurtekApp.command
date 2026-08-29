#!/bin/bash
# Securtek App (macOS client) — finestra Chrome/Edge in modalità --app
#
# 1) Modifica ORIGIN con l'URL del server Mac
# 2) sed -i '' $'s/\r$//' SecurtekApp.command && chmod +x SecurtekApp.command
# 3) Doppio clic per avviare

set -euo pipefail

# --- configura qui l'URL del server Securtek ---
ORIGIN="http://192.168.2.76:8000"
# Esempio in rete locale:
# ORIGIN="http://192.168.1.50:8000"
# -----------------------------------------------

LOGIN="${ORIGIN}/login/?app=1"
PROFILE="${HOME}/Library/Application Support/SecurtekApp"

mkdir -p "${PROFILE}"

CHROME="/Applications/Google Chrome.app"
EDGE="/Applications/Microsoft Edge.app"

if [[ -d "${CHROME}" ]]; then
  open -na "${CHROME}" --args \
    --app="${LOGIN}" \
    --user-data-dir="${PROFILE}" \
    --unsafely-treat-insecure-origin-as-secure="${ORIGIN}" \
    --test-type \
    --disable-features=InsecureDownloadWarnings
elif [[ -d "${EDGE}" ]]; then
  open -na "${EDGE}" --args \
    --app="${LOGIN}" \
    --user-data-dir="${PROFILE}" \
    --unsafely-treat-insecure-origin-as-secure="${ORIGIN}" \
    --test-type \
    --disable-features=InsecureDownloadWarnings
else
  osascript -e 'display alert "Securtek" message "Chrome o Edge non trovati. Installali e riprova." as critical'
  exit 1
fi

# Chiude la finestra Terminale aperta dal doppio clic su .command
osascript >/dev/null 2>&1 <<'APPLESCRIPT' &
tell application "Terminal"
  try
    close front window
  end try
end tell
APPLESCRIPT

exit 0
