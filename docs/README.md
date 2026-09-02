# SECURTEK

Sistema gestionale per la gestione delle pratiche.

## Stack tecnologico

- Python 3.13
- Django 6
- PostgreSQL
- Bootstrap 5
- Tabler
- HTMX
- Alpine.js

## Stato progetto

Versione corrente: vedi file **`VERSION`** nella root del progetto (es. `0.2.1`).

Verifica sul server:

```bash
curl http://127.0.0.1:8000/version/
```

In interfaccia: footer e login (**Securtek v. …**).

Per ogni rilascio aggiornare solo `VERSION` (e `collectstatic` + riavvio Gunicorn sul Mini).

## Documentazione

Consultare la cartella docs/.