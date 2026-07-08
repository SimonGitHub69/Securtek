import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def create_initial_categories(apps, schema_editor):
    CategoriaPratica = apps.get_model("pratiche", "CategoriaPratica")
    initial_categories = [
        "Legge 10",
        "Progetto preliminare per deposito comunale",
        "Progetto preliminare",
        "Progetto esecutivo per deposito comunale",
        "Progetto esecutivo",
    ]

    for denominazione in initial_categories:
        CategoriaPratica.objects.get_or_create(denominazione=denominazione)


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0006_incarichi_tecnici"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CategoriaPratica",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                ("denominazione", models.CharField(max_length=200, unique=True, verbose_name="Denominazione")),
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
                "verbose_name": "Categoria pratica",
                "verbose_name_plural": "Categorie pratiche",
                "ordering": ["denominazione"],
            },
        ),
        migrations.AddField(
            model_name="pratica",
            name="categoria",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pratiche",
                to="pratiche.categoriapratica",
                verbose_name="Categoria",
            ),
        ),
        migrations.RunPython(create_initial_categories, migrations.RunPython.noop),
    ]
