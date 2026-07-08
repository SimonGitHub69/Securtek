import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def migrate_incarichi_tecnici(apps, schema_editor):
    IncaricoTecnico = apps.get_model("pratiche", "IncaricoTecnico")
    Tecnico = apps.get_model("pratiche", "Tecnico")

    for tecnico in Tecnico.objects.exclude(incarico_testo=""):
        denominazione = tecnico.incarico_testo.strip()
        if not denominazione:
            continue

        incarico, _created = IncaricoTecnico.objects.get_or_create(
            denominazione=denominazione,
        )
        tecnico.incarico = incarico
        tecnico.save(update_fields=["incarico"])


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0005_studi_tecnici"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IncaricoTecnico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                ("denominazione", models.CharField(max_length=150, unique=True, verbose_name="Denominazione")),
                ("descrizione", models.TextField(blank=True, verbose_name="Descrizione")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Creato da",
                    ),
                ),
                (
                    "deleted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_deleted",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Eliminato da",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Modificato da",
                    ),
                ),
            ],
            options={
                "verbose_name": "Incarico",
                "verbose_name_plural": "Incarichi",
                "ordering": ["denominazione"],
            },
        ),
        migrations.RenameField(
            model_name="tecnico",
            old_name="incarico",
            new_name="incarico_testo",
        ),
        migrations.AddField(
            model_name="tecnico",
            name="incarico",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tecnici",
                to="pratiche.incaricotecnico",
                verbose_name="Incarico",
            ),
        ),
        migrations.RunPython(migrate_incarichi_tecnici, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="tecnico",
            name="incarico_testo",
        ),
    ]
