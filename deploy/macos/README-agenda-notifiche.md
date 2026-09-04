# Notifiche email agenda su macOS

Securtek può inviare **in automatico** le email di preavviso degli eventi del
calendario lavori (Agenda), in base a:

- flag **Notifica email** sull’evento
- **Giorni preavviso** (es. 7 → email 7 giorni prima della data fine/scadenza)
- parametri SMTP in **Agenda → Parametri mail**
- **Intervallo controllo** e **Servizio automatico** (accendi/spegni) dalla stessa maschera
- servizio **launchd** sul Mac server (loop continuo)

## Prerequisiti

1. Configura SMTP in Securtek (`/agenda/parametri-mail/`) e attiva le notifiche.
2. Imposta intervallo (es. 15 minuti) e lascia il servizio acceso.
3. Prova l’invio di test dalla stessa pagina.
4. Sul Mac Mini (cartella progetto):

```bash
cd /percorso/Securtek
source .venv/bin/activate
python manage.py migrate
python manage.py invia_notifiche_agenda --dry-run
```

## Installazione consigliata (Mac Mini server, senza login)

```bash
chmod +x deploy/macos/run-agenda-notifiche.sh
chmod +x deploy/macos/install-agenda-notifiche.sh
chmod +x deploy/macos/uninstall-agenda-notifiche.sh

sudo ./deploy/macos/install-agenda-notifiche.sh --daemon
```

Il job:

- resta in esecuzione (`KeepAlive`) e controlla secondo l’**intervallo** in Parametri mail
- può essere **spento/acceso** da Securtek senza disinstallare launchd
- invia solo nell’**ora configurata** in Parametri mail (`Ora invio automatico`)
- il **giorno** di invio è `data evento − giorni preavviso`
- funziona anche senza utente loggato
- scrive i log in `logs/agenda-notifiche.log` / `.err`
- registra ogni invio nel pannello **Registro Mail** (`/agenda/log-mail/`)
- lo stato (attivo/spento/fermo) si vede in Parametri mail

## Alternativa (dopo login utente)

```bash
./deploy/macos/install-agenda-notifiche.sh
```

## Prova immediata

```bash
./deploy/macos/run-agenda-notifiche.sh --dry-run
./deploy/macos/run-agenda-notifiche.sh --force
```

`--force` ignora la finestra oraria (utile per test).

## Destinatari

Per ogni evento due, l’email va a:

- personale assegnato all’evento (con email)
- responsabile della pratica (se ha email)
- destinatari di default nei parametri mail

Ogni evento viene notificato **una sola volta** (`notificato_il`).

## Disinstallazione

```bash
./deploy/macos/uninstall-agenda-notifiche.sh
# se era installato come daemon:
sudo ./deploy/macos/uninstall-agenda-notifiche.sh
```

## Stato launchd

```bash
# Daemon
sudo launchctl print system/com.securtek.agenda-notifiche

# Agent
launchctl print "gui/$(id -u)/com.securtek.agenda-notifiche"
```
