import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def migrate_studi_tecnici(apps, schema_editor):
    StudioTecnico = apps.get_model("pratiche", "StudioTecnico")
    Tecnico = apps.get_model("pratiche", "Tecnico")

    for tecnico in Tecnico.objects.exclude(studio_appartenenza_testo=""):
        denominazione = tecnico.studio_appartenenza_testo.strip()
        if not denominazione:
            continue

        studio, _created = StudioTecnico.objects.get_or_create(
            denominazione=denominazione,
        )
        tecnico.studio_appartenenza = studio
        tecnico.save(update_fields=["studio_appartenenza"])


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0004_tecnico_incarico_tecnico_studio_appartenenza"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudioTecnico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                ("denominazione", models.CharField(max_length=200, unique=True, verbose_name="Denominazione")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="Email")),
                ("telefono", models.CharField(blank=True, max_length=30, verbose_name="Telefono")),
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
                "verbose_name": "Studio tecnico",
                "verbose_name_plural": "Studi tecnici",
                "ordering": ["denominazione"],
            },
        ),
        migrations.RenameField(
            model_name="tecnico",
            old_name="studio_appartenenza",
            new_name="studio_appartenenza_testo",
        ),
        migrations.AddField(
            model_name="tecnico",
            name="studio_appartenenza",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tecnici",
                to="pratiche.studiotecnico",
                verbose_name="Studio di appartenenza",
            ),
        ),
        migrations.RunPython(migrate_studi_tecnici, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="tecnico",
            name="studio_appartenenza_testo",
        ),
    ]
