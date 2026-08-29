#!/bin/bash
# Avvio manuale Gunicorn (foreground) — utile per test.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "${ROOT}"

if [[ ! -x "${ROOT}/.venv/bin/gunicorn" ]]; then
  echo "Gunicorn non trovato. Esegui prima:" >&2
  echo "  python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi

mkdir -p "${ROOT}/logs"
export DJANGO_SETTINGS_MODULE=config.settings

exec "${ROOT}/.venv/bin/gunicorn" \
  -c "${ROOT}/deploy/macos/gunicorn.conf.py" \
  config.wsgi:application
