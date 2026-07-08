import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def copy_categories_to_links(apps, schema_editor):
    Pratica = apps.get_model("pratiche", "Pratica")
    PraticaCategoria = apps.get_model("pratiche", "PraticaCategoria")

    through = Pratica._meta.get_field("categorie").remote_field.through
    table_name = through._meta.db_table

    quoted_table_name = schema_editor.quote_name(table_name)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT pratica_id, categoriapratica_id FROM {quoted_table_name}")
        rows = cursor.fetchall()

    for pratica_id, categoria_id in rows:
        PraticaCategoria.objects.get_or_create(
            pratica_id=pratica_id,
            categoria_id=categoria_id,
            versione="",
            defaults={
                "cartella": "",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0008_pratica_categorie_m2m"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PraticaCategoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                ("cartella", models.CharField(blank=True, max_length=500, verbose_name="Cartella")),
                ("versione", models.CharField(blank=True, max_length=50, verbose_name="Versione")),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pratica_collegamenti",
                        to="pratiche.categoriapratica",
                        verbose_name="Categoria",
                    ),
                ),
                (
                    "pratica",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="categoria_collegamenti",
                        to="pratiche.pratica",
                        verbose_name="Pratica",
                    ),
                ),
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
                "verbose_name": "Categoria pratica collegata",
                "verbose_name_plural": "Categorie pratica collegate",
                "ordering": ["categoria__denominazione", "versione"],
            },
        ),
        migrations.RunPython(copy_categories_to_links, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pratica",
            name="categorie",
        ),
        migrations.AddConstraint(
            model_name="praticacategoria",
            constraint=models.UniqueConstraint(
                fields=("pratica", "categoria", "versione"),
                name="unique_pratica_categoria_versione",
            ),
        ),
    ]
