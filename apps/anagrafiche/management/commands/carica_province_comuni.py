from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.anagrafiche.models import Comune, Provincia


class Command(BaseCommand):
    help = "Carica province e comuni italiani dal file data/comuni.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Aggiorna anche i record già presenti",
        )

    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parents[2] / "data" / "comuni.json"
        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f"File non trovato: {data_path}"))
            return

        import json

        with data_path.open(encoding="utf-8") as handle:
            rows = json.load(handle)

        force = options["force"]
        province_created = 0
        province_updated = 0
        comuni_created = 0
        comuni_updated = 0

        with transaction.atomic():
            province_by_sigla = {}
            for row in rows:
                sigla = (row.get("sigla") or "").strip().upper()
                if not sigla:
                    continue
                if sigla in province_by_sigla:
                    continue

                denominazione = (row.get("provincia") or {}).get("nome") or sigla
                codice = (row.get("provincia") or {}).get("codice") or ""
                regione = (row.get("regione") or {}).get("nome") or ""

                provincia, created = Provincia.objects.update_or_create(
                    sigla=sigla,
                    defaults={
                        "denominazione": denominazione,
                        "codice": codice,
                        "regione": regione,
                        "is_active": True,
                        "deleted_at": None,
                        "deleted_by": None,
                    },
                )
                if created:
                    province_created += 1
                else:
                    province_updated += 1
                province_by_sigla[sigla] = provincia

            for row in rows:
                sigla = (row.get("sigla") or "").strip().upper()
                codice_istat = (row.get("codice") or "").strip()
                if not sigla or not codice_istat:
                    continue

                provincia = province_by_sigla.get(sigla)
                if provincia is None:
                    continue

                caps = row.get("cap") or []
                if isinstance(caps, list):
                    cap = caps[0] if caps else ""
                else:
                    cap = str(caps)

                defaults = {
                    "denominazione": (row.get("nome") or "").strip(),
                    "codice_catastale": (row.get("codiceCatastale") or "").strip(),
                    "provincia": provincia,
                    "cap": cap,
                    "popolazione": row.get("popolazione"),
                    "is_active": True,
                    "deleted_at": None,
                    "deleted_by": None,
                }

                existing = Comune.objects.filter(codice_istat=codice_istat).first()
                if existing is None:
                    Comune.objects.create(codice_istat=codice_istat, **defaults)
                    comuni_created += 1
                elif force or not existing.is_active:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save()
                    comuni_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Province create {0}, aggiornate {1}. Comuni creati {2}, aggiornati {3}.".format(
                    province_created,
                    province_updated,
                    comuni_created,
                    comuni_updated,
                )
            )
        )
