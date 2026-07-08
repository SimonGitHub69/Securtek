from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0009_pratica_categoria_cartella_versione"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="praticacategoria",
            name="unique_pratica_categoria_versione",
        ),
        migrations.AddConstraint(
            model_name="praticacategoria",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("pratica", "categoria", "versione"),
                name="unique_pratica_categoria_versione",
            ),
        ),
    ]
