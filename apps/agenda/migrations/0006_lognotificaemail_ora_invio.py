import datetime

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agenda", "0005_alter_eventoagenda_tecnici"),
        ("pratiche", "0022_tecnico_anagrafica"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="ora_invio",
            field=models.TimeField(
                default=datetime.time(8, 0),
                help_text=(
                    "Orario giornaliero di spedizione. L'email parte il giorno "
                    "(data evento - giorni preavviso) a quest'ora."
                ),
                verbose_name="Ora invio automatico",
            ),
        ),
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="ultimo_invio_il",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Ultimo invio automatico",
            ),
        ),
        migrations.AddField(
            model_name="configurazionenotificaemail",
            name="ultimo_invio_esito",
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name="Esito ultimo invio",
            ),
        ),
        migrations.CreateModel(
            name="LogNotificaEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="UUID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creato il")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modificato il")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Eliminato il")),
                ("is_active", models.BooleanField(default=True, verbose_name="Attivo")),
                ("note", models.TextField(blank=True, verbose_name="Note")),
                (
                    "inviata_il",
                    models.DateTimeField(
                        db_index=True,
                        default=django.utils.timezone.now,
                        verbose_name="Data/ora invio",
                    ),
                ),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("automatica", "Automatica"),
                            ("test", "Test"),
                            ("manuale", "Manuale"),
                        ],
                        default="automatica",
                        max_length=20,
                        verbose_name="Tipo",
                    ),
                ),
                (
                    "esito",
                    models.CharField(
                        choices=[
                            ("ok", "Inviata"),
                            ("errore", "Errore"),
                            ("dry_run", "Simulazione"),
                            ("saltata", "Saltata"),
                        ],
                        default="ok",
                        max_length=20,
                        verbose_name="Esito",
                    ),
                ),
                ("oggetto", models.CharField(max_length=300, verbose_name="Oggetto")),
                ("destinatari", models.TextField(verbose_name="Destinatari")),
                ("mittente", models.CharField(blank=True, max_length=254, verbose_name="Mittente")),
                ("errore", models.TextField(blank=True, verbose_name="Errore")),
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
                    "evento",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="log_notifiche",
                        to="agenda.eventoagenda",
                        verbose_name="Evento",
                    ),
                ),
                (
                    "pratica",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="log_notifiche_email",
                        to="pratiche.pratica",
                        verbose_name="Pratica",
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
                "verbose_name": "Log notifica email",
                "verbose_name_plural": "Log notifiche email",
                "ordering": ["-inviata_il", "-id"],
            },
        ),
    ]
