import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.agenda.models import ConfigurazioneNotificaEmail
from apps.agenda.services.notifiche import send_agenda_notifications
from apps.agenda.services.servizio_notifiche import touch_heartbeat


class Command(BaseCommand):
    help = "Invia le email di preavviso per gli eventi agenda in scadenza."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quali notifiche verrebbero inviate senza inviarle.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignora la finestra oraria (ora_invio) e invia subito.",
        )
        parser.add_argument(
            "--loop",
            action="store_true",
            help=(
                "Esegue in continuo (per launchd KeepAlive): rispetta "
                "servizio_attivo e intervallo_controllo_minuti da Parametri mail."
            ),
        )

    def handle(self, *args, **options):
        if options["loop"]:
            self._run_loop(dry_run=options["dry_run"], force=options["force"])
            return
        self._run_once(dry_run=options["dry_run"], force=options["force"] or options["dry_run"])

    def _run_loop(self, dry_run=False, force=False):
        self.stdout.write("Avvio loop notifiche agenda (Ctrl+C per uscire).")
        while True:
            close_old_connections()
            try:
                config = touch_heartbeat()
                interval = max(1, int(config.intervallo_controllo_minuti or 15))

                if not config.servizio_attivo:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Servizio spento da Parametri mail. Prossimo controllo tra {interval} min."
                        )
                    )
                else:
                    self._run_once(dry_run=dry_run, force=force)

                time.sleep(interval * 60)
            except KeyboardInterrupt:
                self.stdout.write("Loop notifiche interrotto.")
                return
            finally:
                close_old_connections()

    def _run_once(self, dry_run=False, force=False):
        config = ConfigurazioneNotificaEmail.get_solo()
        if not config.servizio_attivo and not force and not dry_run:
            self.stdout.write(self.style.WARNING("Servizio automatico spento nei parametri mail."))
            return

        result = send_agenda_notifications(dry_run=dry_run, force=force)

        if result.get("skipped") == "config_disattivata":
            self.stdout.write(self.style.WARNING("Notifiche disattivate nei parametri mail."))
            return

        if result.get("skipped") == "servizio_spento":
            self.stdout.write(self.style.WARNING("Servizio automatico spento nei parametri mail."))
            return

        if result.get("skipped") == "fuori_orario":
            self.stdout.write(
                self.style.WARNING(
                    f"Fuori orario di invio (configurato: {result.get('ora_invio', '?')}). "
                    "Usa --force per inviare subito."
                )
            )
            return

        self.stdout.write(
            f"Eventi con preavviso da inviare oggi: {result['due']} | "
            f"inviati: {result['sent']} | errori: {result['errors']}"
        )

        for detail in result["details"]:
            notify_info = ""
            if detail.get("data_notifica"):
                notify_info = (
                    f" (scadenza {detail['data_termine']:%d/%m/%Y}, "
                    f"preavviso {detail['giorni_preavviso']} gg, "
                    f"invio previsto {detail['data_notifica']:%d/%m/%Y})"
                )
            if detail["status"] == "ok":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Evento {detail['evento_id']}{notify_info}: "
                        f"inviato a {', '.join(detail['recipients'])}"
                    )
                )
            elif detail["status"] == "dry_run":
                self.stdout.write(
                    f"Evento {detail['evento_id']}{notify_info}: "
                    f"dry-run -> {', '.join(detail['recipients'])}"
                )
            elif detail["status"] == "nessun_destinatario":
                self.stdout.write(
                    self.style.WARNING(
                        f"Evento {detail['evento_id']}: nessun destinatario disponibile"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Evento {detail['evento_id']}: {detail.get('error', 'errore sconosciuto')}"
                    )
                )
