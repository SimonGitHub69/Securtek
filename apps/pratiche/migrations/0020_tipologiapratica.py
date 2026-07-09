from django.db import migrations, models
import django.db.models.deletion
import uuid


LEGACY_TIPOLOGIE = {
    "impianto_elettrico": "Impianto elettrico",
    "impianto_termico": "Impianti termici",
    "enea": "ENEA",
    "atex": "ATEX",
}


def seed_tipologie(apps, schema_editor):
    TipologiaPratica = apps.get_model("pratiche", "TipologiaPratica")
    Pratica = apps.get_model("pratiche", "Pratica")
    TemplatePratica = apps.get_model("pratiche", "TemplatePratica")

    tipologia_by_legacy = {}
    for legacy_code, denominazione in LEGACY_TIPOLOGIE.items():
        tipologia, _ = TipologiaPratica.objects.get_or_create(
            denominazione=denominazione,
            defaults={"is_active": True},
        )
        tipologia_by_legacy[legacy_code] = tipologia

    for pratica in Pratica.objects.all():
        legacy_value = getattr(pratica, "tipologia_legacy", "") or "impianto_elettrico"
        pratica.tipologia = tipologia_by_legacy.get(legacy_value, tipologia_by_legacy["impianto_elettrico"])
        pratica.save(update_fields=["tipologia"])

    for template in TemplatePratica.objects.all():
        legacy_value = getattr(template, "tipologia_legacy", "") or "impianto_elettrico"
        template.tipologia = tipologia_by_legacy.get(legacy_value, tipologia_by_legacy["impianto_elettrico"])
        template.save(update_fields=["tipologia"])


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0019_alter_comunicazionepratica_allegato_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TipologiaPratica",
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
                        to="auth.user",
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
                        to="auth.user",
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
                        to="auth.user",
                        verbose_name="Modificato da",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tipologia pratica",
                "verbose_name_plural": "Tipologie pratiche",
                "ordering": ["denominazione"],
            },
        ),
        migrations.RenameField(
            model_name="pratica",
            old_name="tipologia",
            new_name="tipologia_legacy",
        ),
        migrations.RenameField(
            model_name="templatepratica",
            old_name="tipologia",
            new_name="tipologia_legacy",
        ),
        migrations.AddField(
            model_name="pratica",
            name="tipologia",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pratiche",
                to="pratiche.tipologiapratica",
                verbose_name="Tipologia",
            ),
        ),
        migrations.AddField(
            model_name="templatepratica",
            name="tipologia",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="template_pratiche",
                to="pratiche.tipologiapratica",
                verbose_name="Tipologia",
            ),
        ),
        migrations.RunPython(seed_tipologie, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pratica",
            name="tipologia_legacy",
        ),
        migrations.RemoveField(
            model_name="templatepratica",
            name="tipologia_legacy",
        ),
        migrations.AlterField(
            model_name="pratica",
            name="tipologia",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pratiche",
                to="pratiche.tipologiapratica",
                verbose_name="Tipologia",
            ),
        ),
        migrations.AlterField(
            model_name="templatepratica",
            name="tipologia",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="template_pratiche",
                to="pratiche.tipologiapratica",
                unique=True,
                verbose_name="Tipologia",
            ),
        ),
        migrations.AlterModelOptions(
            name="templatepratica",
            options={
                "ordering": ["tipologia__denominazione"],
                "verbose_name": "Template pratica",
                "verbose_name_plural": "Template pratiche",
            },
        ),
    ]
