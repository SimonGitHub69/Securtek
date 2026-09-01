# Securtek App — client macOS

Gli utenti aprono Securtek **dall'app**, non dal browser normale.

## Consigliato sul Mac CLIENT: installer unico

Copia `deploy/macos-client/` sul Mac utente e fai doppio clic su **InstallClient.command**.
Installa helper cartelle (Scegli/Apri sul **quel** Mac) + `Securtek.app`.
Dettagli: `deploy/macos-client/README.md`.

## Solo Securtek.app (senza helper)

1. **Elimina** la vecchia `Securtek.app` sul Desktop (quella che apriva Safari o Chrome normale).
2. Copia `deploy/macos/` sul Mac (o tutto il progetto).
3. Imposta l'IP del server in `build-securtek-app.sh`.
4. Esegui:

```bash
cd ~/Progetti/Securtek
sed -i '' $'s/\r$//' deploy/macos/build-securtek-app.sh
chmod +x deploy/macos/build-securtek-app.sh
./deploy/macos/build-securtek-app.sh
```

Sul Desktop compare **Securtek.app**: doppio clic → finestra dedicata (Edge o Chrome in modalità `--app`), **senza** barra indirizzi e **senza** aprire Safari o una seconda finestra Chrome.

Per cambiare server dopo la creazione:

```bash
nano ~/Desktop/Securtek.app/Contents/MacOS/Securtek
# modifica ORIGIN=...
```

## Requisiti client

- **Microsoft Edge** (consigliato) oppure **Google Chrome**
- Stessa rete del server
- **Python 3** sul client (serve all'helper cartelle; vedi `macos-client/README.md`)
- Niente PostgreSQL / Gunicorn sul client

Safari **non** è supportato come app: apre il browser completo.

### Ricrea Securtek.app

```bash
cd ~/Progetti/Securtek
./deploy/macos/build-securtek-app.sh
```

Per forzare Chrome:

```bash
BROWSER=chrome ./deploy/macos/build-securtek-app.sh
```

## Cartelle (Scegli / Apri)

| Mac | Cosa installare |
|-----|-----------------|
| **Server** (Mini) | `./deploy/macos/install-desktop-helper.sh` |
| **Client** (altro Mac in rete) | `deploy/macos-client/InstallClient.command` |

Senza helper sul client il Finder si apre sul Mini: sul client non succede nulla.

Verifica su ciascun Mac:

```bash
curl http://127.0.0.1:18765/health
```

Dopo aggiornamenti **sul Mini**:

```bash
python manage.py collectstatic --noinput
sudo launchctl kickstart -k system/com.securtek.gunicorn
```
