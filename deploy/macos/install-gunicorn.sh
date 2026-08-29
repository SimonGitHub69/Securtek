#!/bin/bash
# Installa Gunicorn come servizio macOS (launchd): parte al login e resta attivo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GUNICORN="${ROOT}/.venv/bin/gunicorn"
PLIST_SRC="${ROOT}/deploy/macos/com.securtek.gunicorn.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.securtek.gunicorn.plist"
LOG_DIR="${ROOT}/logs"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"
LABEL="com.securtek.gunicorn"

if [[ ! -x "${GUNICORN}" ]]; then
  echo "Gunicorn non trovato in ${GUNICORN}" >&2
  echo "Esegui: source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"
mkdir -p "${HOME}/Library/LaunchAgents"

sed -e "s|__PROJECT_ROOT__|${ROOT}|g" "${PLIST_SRC}" > "${PLIST_DST}"

# Pulisci eventuali stati launchd residui (causa tipica di Bootstrap failed: 5).
unload_existing() {
  launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
  launchctl bootout "${DOMAIN}" "${PLIST_DST}" 2>/dev/null || true
  launchctl unload -w "${PLIST_DST}" 2>/dev/null || true
  launchctl disable "${DOMAIN}/${LABEL}" 2>/dev/null || true
  sleep 1
}

unload_existing

load_ok=0
if launchctl bootstrap "${DOMAIN}" "${PLIST_DST}" 2>/tmp/securtek-launchctl.err; then
  load_ok=1
else
  echo "bootstrap fallito, provo con launchctl load -w..." >&2
  cat /tmp/securtek-launchctl.err >&2 || true
  unload_existing
  if launchctl load -w "${PLIST_DST}" 2>/tmp/securtek-launchctl.err; then
    load_ok=1
  fi
fi

if [[ "${load_ok}" -ne 1 ]]; then
  echo >&2
  echo "ERRORE: impossibile registrare il servizio launchd." >&2
  echo "Dettaglio:" >&2
  cat /tmp/securtek-launchctl.err >&2 || true
  echo >&2
  echo "Avvio manuale (funziona subito, resta aperto il Terminale):" >&2
  echo "  ${ROOT}/deploy/macos/start-gunicorn.sh" >&2
  echo >&2
  echo "Se sei collegato via SSH senza sessione grafica, apri Terminale" >&2
  echo "sul Mac (login desktop) e rilancia questo script." >&2
  exit 1
fi

launchctl enable "${DOMAIN}/${LABEL}" 2>/dev/null || true
launchctl kickstart -k "${DOMAIN}/${LABEL}" 2>/dev/null \
  || launchctl start "${LABEL}" 2>/dev/null \
  || true

echo "Servizio installato: ${PLIST_DST}"
echo "WorkingDirectory: ${ROOT}"
echo "Securtek in ascolto su: http://0.0.0.0:8000"
echo "Log: ${LOG_DIR}/gunicorn.*.log"
echo
echo "Comandi utili:"
echo "  launchctl kickstart -k ${DOMAIN}/${LABEL}   # riavvia"
echo "  launchctl bootout ${DOMAIN}/${LABEL}        # ferma/disinstalla"
echo "  ./deploy/macos/start-gunicorn.sh            # avvio manuale"
