from django.core.management.base import BaseCommand

from apps.agenda.services.notifiche import send_agenda_notifications


class Command(BaseCommand):
    help = "Invia le email di preavviso per gli eventi agenda in scadenza."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quali notifiche verrebbero inviate senza inviarle.",
        )

    def handle(self, *args, **options):
        result = send_agenda_notifications(dry_run=options["dry_run"])

        if result.get("skipped"):
            self.stdout.write(self.style.WARNING("Notifiche disattivate nei parametri mail."))
            return

        self.stdout.write(
            f"Eventi con preavviso da inviare oggi: {result['due']} | inviati: {result['sent']} | errori: {result['errors']}"
        )

        for detail in result["details"]:
            notify_info = ""
            if detail.get("data_notifica"):
                notify_info = (
                    f" (scadenza {detail['data_termine']:%d/%m/%Y}, "
                    f"preavviso {detail['giorni_preavviso']} gg, invio previsto {detail['data_notifica']:%d/%m/%Y})"
                )
            if detail["status"] == "ok":
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Evento {detail['evento_id']}{notify_info}: inviato a {', '.join(detail['recipients'])}"
                    )
                )
            elif detail["status"] == "dry_run":
                self.stdout.write(
                    f"Evento {detail['evento_id']}{notify_info}: dry-run -> {', '.join(detail['recipients'])}"
                )
            elif detail["status"] == "nessun_destinatario":
                self.stdout.write(
                    self.style.WARNING(f"Evento {detail['evento_id']}: nessun destinatario disponibile")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Evento {detail['evento_id']}: {detail.get('error', 'errore sconosciuto')}")
                )
