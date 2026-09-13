#!/bin/bash
# Doppio clic sul Mini / Mac di sviluppo: crea lo zip installer client.
cd "$(dirname "$0")/.." || exit 1
chmod +x scripts/build-macos-client-installer.sh
exec ./scripts/build-macos-client-installer.sh
