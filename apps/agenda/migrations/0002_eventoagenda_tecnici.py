from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pratiche", "0020_tipologiapratica"),
        ("agenda", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoagenda",
            name="tecnici",
            field=models.ManyToManyField(
                blank=True,
                related_name="eventi_agenda",
                to="pratiche.tecnico",
                verbose_name="Tecnici",
            ),
        ),
    ]
