#!/bin/bash
# Crea solo Securtek.app sul Desktop (senza helper cartelle).
cd "$(dirname "$0")" || exit 1
perl -pi -e 's/\r\n?/\n/g' ./install-client.sh ./create-app.sh 2>/dev/null || true
chmod +x ./install-client.sh ./create-app.sh
export SECURTEK_APP_ONLY=1
exec ./install-client.sh
