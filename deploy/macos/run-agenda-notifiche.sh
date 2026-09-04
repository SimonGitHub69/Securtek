#!/bin/bash
# Esegue l'invio delle mail di preavviso agenda (usato da launchd).
# Con --loop resta in esecuzione e legge intervallo/servizio da Parametri mail.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

cd "${ROOT}"

if [[ ! -x "${PYTHON}" ]]; then
    echo "Python virtuale non trovato: ${PYTHON}" >&2
    exit 1
fi

# Se chiamato senza argomenti da launchd, avvia il loop continuo.
if [[ $# -eq 0 ]]; then
    exec "${PYTHON}" manage.py invia_notifiche_agenda --loop
fi

exec "${PYTHON}" manage.py invia_notifiche_agenda "$@"
