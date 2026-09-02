#!/bin/bash
# Doppio clic: crea solo Securtek.app sul Desktop (niente helper).
cd "$(dirname "$0")" || exit 1
perl -pi -e 's/\r\n?/\n/g' ./create-app.sh ./CreateApp.command 2>/dev/null || true
chmod +x ./create-app.sh ./CreateApp.command
./create-app.sh
status=$?
echo
read -r -p "Premi Invio per chiudere..." _
exit "${status}"
