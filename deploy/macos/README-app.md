# Securtek App — client macOS

Gli utenti aprono Securtek **dall’app**, non dal browser.

## Consigliato: Securtek.app (niente Terminale)

1. Copia `deploy/macos/` sul Mac (o tutto il progetto).
2. Imposta l’IP del server in `build-securtek-app.sh` oppure dopo la creazione nell’eseguibile.
3. Esegui:

```bash
cd ~/Progetti/Securtek
sed -i '' $'s/\r$//' deploy/macos/build-securtek-app.sh
chmod +x deploy/macos/build-securtek-app.sh
./deploy/macos/build-securtek-app.sh
```

Sul Desktop compare **Securtek.app**: doppio clic, niente Terminale.

Per cambiare server dopo la creazione:

```bash
nano ~/Desktop/Securtek.app/Contents/MacOS/Securtek
# modifica ORIGIN=...
```

## Alternativa: SecurtekApp.command

Apre il Terminale (poi si chiude). Preferisci `Securtek.app`.

## Requisiti client

- Chrome o Edge
- Stessa rete del server
- Niente Python / PostgreSQL / Gunicorn
