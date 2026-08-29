# Apertura cartelle e file nativi (Windows)

Le azioni **Apri cartella di origine** e **Apri con applicazione originale** nella scheda pratica
vengono eseguite dal processo Django **sul computer locale** tramite `explorer.exe`.

## Requisiti

- Securtek deve girare **sulla stessa postazione Windows** dove sono memorizzati i file di pratica
  (es. `runserver` locale), non su un server remoto accessibile solo via browser.
- L'utente deve avere una **sessione grafica** attiva (Explorer disponibile).
- I percorsi salvati nelle categorie pratica devono essere path assoluti o espandibili e leggibili
  dal processo del server.

## Comportamento in primo piano

Dopo l'apertura, Securtek tenta di portare Explorer in primo piano **senza PowerShell/cmd**
(per evitare il flash nero della console). Windows limita spesso il focus quando la richiesta
parte da un processo in background (Django avviato da terminale o servizio).

Se Explorer si apre ma resta **dietro al browser**:

1. Clicca **una volta** sull'icona di Explorer nella **barra delle applicazioni**.
2. In alternativa usa **Alt+Tab** per passare alla finestra Explorer.

## Limitazione server remoto

Se il browser punta a Django su un'altra macchina, l'apertura desktop avviene **sul server**,
non sul PC dell'utente. Per l'uso in studio, eseguire sempre l'applicazione in locale su Windows.
