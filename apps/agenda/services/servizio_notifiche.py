"""Stato del servizio automatico notifiche mail (launchd / heartbeat)."""

from __future__ import annotations

import platform
import subprocess
from datetime import timedelta

from django.utils import timezone

from apps.agenda.models import ConfigurazioneNotificaEmail

LAUNCHD_LABEL = "com.securtek.agenda-notifiche"


def _run_cmd(args: list[str], timeout: float = 3.0) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return completed.returncode, output
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def launchd_loaded() -> bool | None:
    """True/False se launchd ha il job; None se non verificabile (es. Windows)."""
    if platform.system() != "Darwin":
        return None

    code, out = _run_cmd(["launchctl", "print", f"system/{LAUNCHD_LABEL}"])
    if code == 0 and LAUNCHD_LABEL in out:
        return True

    try:
        import os

        uid = os.getuid()
    except AttributeError:
        uid = None

    if uid is not None:
        code, out = _run_cmd(["launchctl", "print", f"gui/{uid}/{LAUNCHD_LABEL}"])
        if code == 0 and LAUNCHD_LABEL in out:
            return True

    return False


def process_running() -> bool | None:
    """True se il loop/job Python e' in esecuzione; None se non verificabile."""
    system = platform.system()
    if system == "Windows":
        return None

    patterns = (
        "invia_notifiche_agenda",
        "run-agenda-notifiche.sh",
    )
    for pattern in patterns:
        code, out = _run_cmd(["pgrep", "-fl", pattern])
        if code == 0 and out.strip():
            return True
    return False


def heartbeat_fresh(config: ConfigurazioneNotificaEmail | None = None) -> bool:
    config = config or ConfigurazioneNotificaEmail.get_solo()
    if not config.ultimo_controllo_il:
        return False
    interval = max(1, int(config.intervallo_controllo_minuti or 15))
    # Tolleranza: 2 cicli + 2 minuti
    max_age = timedelta(minutes=(interval * 2) + 2)
    return timezone.now() - config.ultimo_controllo_il <= max_age


def touch_heartbeat(config: ConfigurazioneNotificaEmail | None = None) -> ConfigurazioneNotificaEmail:
    config = config or ConfigurazioneNotificaEmail.get_solo()
    config.ultimo_controllo_il = timezone.now()
    config.save(update_fields=["ultimo_controllo_il", "updated_at"])
    return config


def get_servizio_status(config: ConfigurazioneNotificaEmail | None = None) -> dict:
    """
    Stato aggregato per la UI Parametri mail.

    stati:
      - spento: servizio_attivo=False (spegnimento da app)
      - attivo: heartbeat fresco e/o processo/launchd ok
      - inattivo: servizio acceso ma job non risponde / non installato
      - sconosciuto: piattaforma senza check OS (es. Windows di sviluppo)
    """
    config = config or ConfigurazioneNotificaEmail.get_solo()
    loaded = launchd_loaded()
    running = process_running()
    fresh = heartbeat_fresh(config)
    interval = max(1, int(config.intervallo_controllo_minuti or 15))

    if not config.servizio_attivo:
        stato = "spento"
        etichetta = "Spento"
        dettaglio = (
            "Il servizio automatico e' spento da Parametri mail. "
            "Non verranno inviate mail finche' non lo riaccendi."
        )
        colore = "secondary"
    elif fresh or running is True:
        stato = "attivo"
        etichetta = "Attivo"
        dettaglio = "Il job di controllo mail sta girando sul server."
        colore = "success"
    elif loaded is False and running is False and not fresh:
        stato = "inattivo"
        etichetta = "Non installato / fermo"
        dettaglio = (
            "Servizio acceso in app ma il job sul Mac non risulta in esecuzione. "
            "Installa o riavvia con: sudo ./deploy/macos/install-agenda-notifiche.sh --daemon"
        )
        colore = "warning"
    elif loaded is None and running is None and not fresh:
        stato = "sconosciuto"
        etichetta = "Stato non verificabile qui"
        dettaglio = (
            "Su questo PC non si puo' leggere launchd. Controlla lo stato sul Mac Mini "
            "dopo aver salvato i parametri."
        )
        colore = "secondary"
    else:
        stato = "inattivo"
        etichetta = "In attesa / fermo"
        dettaglio = (
            "Nessun controllo recente dal servizio. "
            "Verifica launchd sul Mac Mini o attendi il prossimo ciclo."
        )
        colore = "warning"

    return {
        "stato": stato,
        "etichetta": etichetta,
        "dettaglio": dettaglio,
        "colore": colore,
        "servizio_attivo": config.servizio_attivo,
        "intervallo_controllo_minuti": interval,
        "ultimo_controllo_il": config.ultimo_controllo_il,
        "launchd_loaded": loaded,
        "process_running": running,
        "heartbeat_fresh": fresh,
        "notifiche_attive": config.attiva,
    }
