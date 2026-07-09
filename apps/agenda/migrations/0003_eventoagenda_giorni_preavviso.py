from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0002_eventoagenda_tecnici"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoagenda",
            name="giorni_preavviso",
            field=models.PositiveSmallIntegerField(default=7, verbose_name="Giorni preavviso"),
        ),
    ]
