from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0003_eventoagenda_giorni_preavviso"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="verifica_certificato_ssl",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Disattiva solo se il certificato del server non corrisponde al nome host SMTP."
                ),
                verbose_name="Verifica certificato SSL",
            ),
        ),
    ]
