from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0006_lognotificaemail_ora_invio"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="intervallo_controllo_minuti",
            field=models.PositiveSmallIntegerField(
                default=15,
                help_text="Ogni quanti minuti il servizio controlla se ci sono mail da inviare.",
                verbose_name="Intervallo controllo (minuti)",
            ),
        ),
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="servizio_attivo",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Se disattivo, il job sul Mac Mini resta installato ma non invia mail "
                    "fino a nuova accensione da Parametri mail."
                ),
                verbose_name="Servizio automatico attivo",
            ),
        ),
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="ultimo_controllo_il",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Ultimo controllo servizio",
            ),
        ),
    ]
