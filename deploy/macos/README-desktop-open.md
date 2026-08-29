# Apertura cartelle e file nativi (macOS)

Le azioni **Apri cartella di origine** e **Apri con applicazione originale** nella scheda pratica
vengono eseguite dal processo Django sul computer locale tramite il comando `open` di macOS.

## Requisiti

- Securtek deve girare **sulla stessa Mac** dove sono memorizzati i file di pratica
  (es. `runserver` locale o app desktop), non su un server remoto accessibile solo via browser.
- L'utente deve avere una **sessione grafica** attiva (Finder disponibile).
- I percorsi salvati nelle categorie pratica devono essere path assoluti o espandibili (`~`)
  e leggibili dal processo del server.

## Comandi usati

| Azione | Comando |
|--------|---------|
| Cartella con file selezionato | `open -R /percorso/file` |
| Solo cartella | `open /percorso/cartella` |
| File con app predefinita | `open /percorso/file` |

## Verifica rapida

1. Avviare Django in locale: `.venv/bin/python manage.py runserver`
2. Aprire una pratica con cartella collegata su disco locale.
3. Cliccare l'icona cartella accanto a un file: Finder deve aprirsi sulla cartella corretta con il file evidenziato.
4. Cliccare l'icona Word/Excel: il file deve aprirsi nell'applicazione predefinita.

## Limitazione

Se il browser punta a un server su un'altra macchina, l'apertura desktop avviene **sul server**,
non sul client. Per l'uso in studio, eseguire sempre l'applicazione in locale su macOS.
