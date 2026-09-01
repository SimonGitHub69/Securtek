#!/bin/bash
# Installa l'helper cartelle come LaunchAgent (GUI al LOGIN — obbligatorio sul Mac SERVER).
# Gunicorn LaunchDaemon NON può mostrare finestre: senza questo helper Scegli/Apri falliscono.
#
# Per un Mac CLIENT (stessa rete, senza Django): usa deploy/macos-client/InstallClient.command
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HELPER="${ROOT}/scripts/securtek_desktop_helper.py"
PLIST_DST="${HOME}/Library/LaunchAgents/com.securtek.desktop-helper.plist"
LOG_DIR="${ROOT}/logs"
DOMAIN="gui/$(id -u)"
LABEL="com.securtek.desktop-helper"

if [[ ! -f "${HELPER}" ]]; then
  echo "Helper non trovato: ${HELPER}" >&2
  exit 1
fi

PYTHON3=""
if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PYTHON3="${ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON3="$(command -v python3)"
else
  echo "Python3 non trovato." >&2
  exit 1
fi

# Normalizza fine riga Windows se presenti
if grep -q $'\r' "${HELPER}" 2>/dev/null; then
  sed -i '' $'s/\r$//' "${HELPER}"
fi

mkdir -p "${HOME}/Library/LaunchAgents"
mkdir -p "${LOG_DIR}"

cat > "${PLIST_DST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON3}</string>
        <string>${HELPER}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/desktop-helper.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/desktop-helper.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
launchctl bootout "${DOMAIN}" "${PLIST_DST}" 2>/dev/null || true
sleep 1

if ! launchctl bootstrap "${DOMAIN}" "${PLIST_DST}" 2>/tmp/securtek-helper-launchctl.err; then
  echo "bootstrap fallito, provo load -w..." >&2
  cat /tmp/securtek-helper-launchctl.err >&2 || true
  launchctl load -w "${PLIST_DST}"
fi

launchctl enable "${DOMAIN}/${LABEL}" 2>/dev/null || true
launchctl kickstart -k "${DOMAIN}/${LABEL}" 2>/dev/null || true

sleep 1
echo "Helper installato: ${PLIST_DST}"
echo "Python: ${PYTHON3}"
if curl -fsS "http://127.0.0.1:18765/health" ; then
  echo
  echo "OK — helper in ascolto."
else
  echo
  echo "ATTENZIONE: health non risponde. Controlla:"
  echo "  cat ${LOG_DIR}/desktop-helper.err.log"
  echo "  launchctl print ${DOMAIN}/${LABEL}"
  echo
  echo "Avvio manuale di prova:"
  echo "  ${PYTHON3} ${HELPER}"
fi
