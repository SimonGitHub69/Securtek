from django.db import migrations, models


def copy_single_categories_to_m2m(apps, schema_editor):
    Pratica = apps.get_model("pratiche", "Pratica")

    for pratica in Pratica.objects.exclude(categoria_singola_id=None):
        pratica.categorie.add(pratica.categoria_singola_id)


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0007_categorie_pratiche"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pratica",
            old_name="categoria",
            new_name="categoria_singola",
        ),
        migrations.AddField(
            model_name="pratica",
            name="categorie",
            field=models.ManyToManyField(
                blank=True,
                related_name="pratiche",
                to="pratiche.categoriapratica",
                verbose_name="Categorie",
            ),
        ),
        migrations.RunPython(copy_single_categories_to_m2m, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="pratica",
            name="categoria_singola",
        ),
    ]
