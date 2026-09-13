#!/usr/bin/env bash
# Crea dist/Securtek-client-mac-vVERSION.zip (installer autoinstallante client Mac)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY="$(command -v python3)"
fi
exec "${PY}" "${ROOT}/scripts/build-macos-client-installer.py"
