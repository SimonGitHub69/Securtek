# Securtek su macOS — Gunicorn

Sul Mac server non usare `runserver`. Usa **Gunicorn**.

## 1. Una tantum (setup progetto)

Nella cartella del progetto:

```bash
cd /percorso/Securtek
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Prepara il `.env` di produzione, ad esempio:

```env
DEBUG=False
SECRET_KEY=...chiave-lunga...
ALLOWED_HOSTS=127.0.0.1,localhost,192.168.x.x,nome-del-mac.local
DATABASE_URL=postgres://securtek:PASSWORD@127.0.0.1:5432/securtek
SITE_URL=http://192.168.x.x:8000
```

Poi:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # se serve
```

## 2. Avvio di prova (manuale)

```bash
chmod +x deploy/macos/start-gunicorn.sh
./deploy/macos/start-gunicorn.sh
```

Apri da un altro PC: `http://IP-DEL-MAC:8000`  
Oppure dall’app Securtek con `Origin` puntato a quell’IP.

Ferma con `Ctrl+C`.

## 3. Avvio automatico (consigliato: senza login)

Per un Mac server che deve ripartire **all’accensione senza fare accesso**,
usa il **LaunchDaemon** (richiede `sudo` una volta):

```bash
chmod +x deploy/macos/install-gunicorn-daemon.sh
sudo ./deploy/macos/install-gunicorn-daemon.sh
```

Così Gunicorn:
- parte all’accensione del Mac (**senza login**)
- gira come l’utente che ha lanciato `sudo` (es. `macminiserver`)
- si riavvia se si chiude
- ascolta su porta **8000**
- rimuove automaticamente il vecchio LaunchAgent utente (evita doppio servizio)

### Riavvio / stop (Daemon)

```bash
sudo launchctl kickstart -k system/com.securtek.gunicorn
sudo launchctl bootout system/com.securtek.gunicorn
sudo launchctl print system/com.securtek.gunicorn
```

### Alternativa: solo al login (LaunchAgent)

Se preferisci che parta solo dopo il login desktop:

```bash
chmod +x deploy/macos/install-gunicorn.sh
./deploy/macos/install-gunicorn.sh
```

```bash
launchctl kickstart -k "gui/$(id -u)/com.securtek.gunicorn"
launchctl bootout "gui/$(id -u)/com.securtek.gunicorn"
```

Non installare Agent e Daemon insieme.

## 4. Client Mac (app)

Su ogni Mac utente copia `deploy/macos/SecurtekApp.command` e imposta:

```bash
ORIGIN="http://IP-DEL-SERVER:8000"
```

Poi:

```bash
chmod +x SecurtekApp.command
```

Guida client: `deploy/macos/README-app.md`

## Log

- `logs/gunicorn.access.log`
- `logs/gunicorn.error.log`
