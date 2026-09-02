#!/bin/bash
# Ripara Securtek.app (permessi, quarantena, launcher aggiornato).
set -euo pipefail
cd "$(dirname "$0")" || exit 1
perl -pi -e 's/\r\n?/\n/g' ./install-client.sh ./repair-app.sh ./SecurtekLauncher.template 2>/dev/null || true
chmod +x ./install-client.sh ./repair-app.sh
export SECURTEK_APP_ONLY=1
exec ./install-client.sh
