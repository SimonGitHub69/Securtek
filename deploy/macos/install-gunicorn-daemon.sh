#!/bin/bash
# Installa Gunicorn come LaunchDaemon: parte all'accensione del Mac SENZA login.
# Richiede sudo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GUNICORN="${ROOT}/.venv/bin/gunicorn"
PLIST_SRC="${ROOT}/deploy/macos/com.securtek.gunicorn.daemon.plist"
PLIST_DST="/Library/LaunchDaemons/com.securtek.gunicorn.plist"
AGENT_PLIST="${HOME}/Library/LaunchAgents/com.securtek.gunicorn.plist"
LOG_DIR="${ROOT}/logs"
LABEL="com.securtek.gunicorn"
SYSTEM_DOMAIN="system"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Questo script richiede sudo." >&2
  echo "Esegui: sudo $0" >&2
  exit 1
fi

# Utente reale (non root) che invoca sudo
RUN_USER="${SUDO_USER:-}"
if [[ -z "${RUN_USER}" || "${RUN_USER}" == "root" ]]; then
  echo "Impossibile determinare l'utente non-root (SUDO_USER vuoto)." >&2
  echo "Esegui come: sudo -u <tuo-utente> non va; usa: sudo ./deploy/macos/install-gunicorn-daemon.sh" >&2
  exit 1
fi

RUN_HOME="$(dscl . -read "/Users/${RUN_USER}" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
if [[ -z "${RUN_HOME}" ]]; then
  RUN_HOME="$(eval echo "~${RUN_USER}")"
fi
RUN_GROUP="$(id -gn "${RUN_USER}")"
RUN_UID="$(id -u "${RUN_USER}")"

if [[ ! -x "${GUNICORN}" ]]; then
  echo "Gunicorn non trovato in ${GUNICORN}" >&2
  echo "Esegui (come ${RUN_USER}): source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "${PLIST_SRC}" ]]; then
  echo "Template mancante: ${PLIST_SRC}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"
chown "${RUN_USER}:${RUN_GROUP}" "${LOG_DIR}"

# Rimuovi LaunchAgent utente (evita doppio Gunicorn sulla porta 8000)
remove_agent() {
  if [[ -f "${AGENT_PLIST}" ]]; then
    launchctl bootout "gui/${RUN_UID}/${LABEL}" 2>/dev/null || true
    launchctl bootout "gui/${RUN_UID}" "${AGENT_PLIST}" 2>/dev/null || true
    launchctl asuser "${RUN_UID}" launchctl unload -w "${AGENT_PLIST}" 2>/dev/null || true
    rm -f "${AGENT_PLIST}"
    echo "Rimosso LaunchAgent utente: ${AGENT_PLIST}"
  else
    launchctl bootout "gui/${RUN_UID}/${LABEL}" 2>/dev/null || true
  fi
}

remove_daemon() {
  launchctl bootout "${SYSTEM_DOMAIN}/${LABEL}" 2>/dev/null || true
  launchctl bootout "${SYSTEM_DOMAIN}" "${PLIST_DST}" 2>/dev/null || true
  launchctl unload -w "${PLIST_DST}" 2>/dev/null || true
  sleep 1
}

remove_agent
remove_daemon

# Ferma eventuali gunicorn manuali sulla stessa config (best effort)
pkill -f "${ROOT}/.venv/bin/gunicorn" 2>/dev/null || true
sleep 1

TMP_PLIST="$(mktemp /tmp/com.securtek.gunicorn.XXXXXX.plist)"
sed \
  -e "s|__PROJECT_ROOT__|${ROOT}|g" \
  -e "s|__RUN_USER__|${RUN_USER}|g" \
  -e "s|__RUN_GROUP__|${RUN_GROUP}|g" \
  -e "s|__RUN_HOME__|${RUN_HOME}|g" \
  "${PLIST_SRC}" > "${TMP_PLIST}"

install -o root -g wheel -m 644 "${TMP_PLIST}" "${PLIST_DST}"
rm -f "${TMP_PLIST}"

if ! launchctl bootstrap "${SYSTEM_DOMAIN}" "${PLIST_DST}" 2>/tmp/securtek-daemon-launchctl.err; then
  echo "bootstrap system fallito, provo launchctl load -w..." >&2
  cat /tmp/securtek-daemon-launchctl.err >&2 || true
  if ! launchctl load -w "${PLIST_DST}" 2>/tmp/securtek-daemon-launchctl.err; then
    echo >&2
    echo "ERRORE: impossibile registrare il LaunchDaemon." >&2
    cat /tmp/securtek-daemon-launchctl.err >&2 || true
    echo >&2
    echo "Avvio manuale: ${ROOT}/deploy/macos/start-gunicorn.sh" >&2
    exit 1
  fi
fi

launchctl enable "${SYSTEM_DOMAIN}/${LABEL}" 2>/dev/null || true
launchctl kickstart -k "${SYSTEM_DOMAIN}/${LABEL}" 2>/dev/null \
  || launchctl start "${LABEL}" 2>/dev/null \
  || true

sleep 1

echo
echo "LaunchDaemon installato: ${PLIST_DST}"
echo "Esegue come: ${RUN_USER}:${RUN_GROUP}"
echo "WorkingDirectory: ${ROOT}"
echo "Parte all'accensione del Mac (senza login)."
echo "Securtek: http://0.0.0.0:8000"
echo "Log: ${LOG_DIR}/gunicorn.*.log"
echo
echo "Comandi utili:"
echo "  sudo launchctl kickstart -k system/${LABEL}   # riavvia"
echo "  sudo launchctl bootout system/${LABEL}        # ferma"
echo "  sudo launchctl print system/${LABEL}          # stato"
echo "  ./deploy/macos/start-gunicorn.sh              # avvio manuale"
echo
echo "Verifica:"
echo "  curl -I http://127.0.0.1:8000/"
echo "  sudo launchctl print system/${LABEL} | head"
