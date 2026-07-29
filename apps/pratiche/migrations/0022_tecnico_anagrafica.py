import django.db.models.deletion
from django.db import migrations, models


def backfill_tecnico_anagrafica(apps, schema_editor):
    Tecnico = apps.get_model("pratiche", "Tecnico")
    for tecnico in Tecnico.objects.select_related("pratica").iterator():
        if tecnico.pratica_id and not tecnico.anagrafica_id:
            tecnico.anagrafica_id = tecnico.pratica.cliente_id
            tecnico.save(update_fields=["anagrafica_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("anagrafiche", "0004_anagrafica_logo"),
        ("pratiche", "0021_rename_studio_tecnico_labels_to_esterni"),
    ]

    operations = [
        migrations.AddField(
            model_name="tecnico",
            name="anagrafica",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="personale",
                to="anagrafiche.anagrafica",
                verbose_name="Anagrafica",
            ),
        ),
        migrations.AlterField(
            model_name="tecnico",
            name="pratica",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tecnici",
                to="pratiche.pratica",
                verbose_name="Pratica",
            ),
        ),
        migrations.RunPython(backfill_tecnico_anagrafica, migrations.RunPython.noop),
    ]
