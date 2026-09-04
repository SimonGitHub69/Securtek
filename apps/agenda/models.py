from datetime import time, timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.pratiche.models import Pratica, Tecnico


class EventoAgenda(BaseModel):
    class Tipo(models.TextChoices):
        EVENTO = "evento", "Evento"
        SCADENZA = "scadenza", "Scadenza"
        LAVORO = "lavoro", "Lavoro"

    class Stato(models.TextChoices):
        PROGRAMMATO = "programmato", "Programmato"
        IN_CORSO = "in_corso", "In corso"
        COMPLETATO = "completato", "Completato"
        ANNULLATO = "annullato", "Annullato"

    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.CASCADE,
        related_name="eventi_agenda",
        verbose_name="Pratica",
    )
    titolo = models.CharField("Titolo", max_length=200)
    tipo = models.CharField("Tipo", max_length=20, choices=Tipo.choices, default=Tipo.LAVORO)
    stato = models.CharField("Stato", max_length=20, choices=Stato.choices, default=Stato.PROGRAMMATO)
    data_inizio = models.DateField("Data inizio", default=timezone.localdate)
    ora_inizio = models.TimeField("Ora inizio", null=True, blank=True)
    data_fine = models.DateField("Data fine / scadenza", null=True, blank=True)
    ora_fine = models.TimeField("Ora fine", null=True, blank=True)
    notifica_email = models.BooleanField("Notifica email", default=True)
    giorni_preavviso = models.PositiveSmallIntegerField("Giorni preavviso", default=7)
    notificato_il = models.DateTimeField("Notificato il", null=True, blank=True)
    descrizione = models.TextField("Descrizione", blank=True)
    tecnici = models.ManyToManyField(
        Tecnico,
        related_name="eventi_agenda",
        verbose_name="Personale",
        blank=True,
    )

    class Meta:
        verbose_name = "Evento agenda"
        verbose_name_plural = "Eventi agenda"
        ordering = ["data_inizio", "ora_inizio", "titolo"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titolo}"

    @property
    def data_termine(self):
        return self.data_fine or self.data_inizio

    @property
    def data_notifica(self):
        """Data in cui inviare l'email di preavviso (data_termine - giorni_preavviso)."""
        return self.data_termine - timedelta(days=self.giorni_preavviso)

    @property
    def is_scaduto(self):
        return (
            self.tipo == self.Tipo.SCADENZA
            and self.data_termine < timezone.localdate()
            and self.stato not in {self.Stato.COMPLETATO, self.Stato.ANNULLATO}
        )


class ConfigurazioneNotificaEmail(BaseModel):
    attiva = models.BooleanField("Attiva", default=False)
    host = models.CharField("Server SMTP", max_length=200, blank=True)
    porta = models.PositiveIntegerField("Porta", default=587)
    usa_tls = models.BooleanField("Usa TLS", default=True)
    usa_ssl = models.BooleanField("Usa SSL", default=False)
    verifica_certificato_ssl = models.BooleanField(
        "Verifica certificato SSL",
        default=True,
        help_text=(
            "Disattiva solo se il certificato del server non corrisponde al nome host SMTP."
        ),
    )
    username = models.CharField("Username", max_length=200, blank=True)
    password = models.CharField("Password", max_length=200, blank=True)
    mittente = models.EmailField("Mittente", blank=True)
    destinatari_default = models.TextField("Destinatari predefiniti", blank=True)
    template_oggetto = models.CharField(
        "Modello oggetto mail",
        max_length=300,
        blank=True,
        default="[Securtek] Promemoria {{data}} - {{titolo}}",
        help_text="Usa segnaposto come {{titolo}}, {{data}}, {{pratica_codice}}.",
    )
    template_corpo = models.TextField(
        "Modello testo mail",
        blank=True,
        default=(
            "Promemoria: {{titolo}}\n"
            "\n"
            "Tipo: {{tipo}}\n"
            "Pratica: {{pratica_codice}} - {{pratica_titolo}}\n"
            "Cliente: {{cliente}}\n"
            "Data: {{data}}\n"
            "Ora: {{ora}}\n"
            "\n"
            "{{descrizione}}\n"
            "\n"
            "Apri pratica: {{url_pratica}}"
        ),
        help_text=(
            "Testo dell'email di preavviso. Segnaposto disponibili: "
            "{{titolo}}, {{tipo}}, {{pratica_codice}}, {{pratica_titolo}}, {{cliente}}, "
            "{{data}}, {{ora}}, {{descrizione}}, {{url_pratica}}, {{giorni_preavviso}}, "
            "{{data_notifica}}."
        ),
    )
    giorni_preavviso = models.PositiveSmallIntegerField("Giorni preavviso", default=7)
    ora_invio = models.TimeField(
        "Ora invio automatico",
        default=time(8, 0),
        help_text=(
            "Orario giornaliero di spedizione. L'email parte il giorno "
            "(data evento - giorni preavviso) a quest'ora."
        ),
    )
    servizio_attivo = models.BooleanField(
        "Servizio automatico attivo",
        default=True,
        help_text=(
            "Se disattivo, il job sul Mac Mini resta installato ma non invia mail "
            "fino a nuova accensione da Parametri mail."
        ),
    )
    intervallo_controllo_minuti = models.PositiveSmallIntegerField(
        "Intervallo controllo (minuti)",
        default=15,
        help_text="Ogni quanti minuti il servizio controlla se ci sono mail da inviare.",
    )
    ultimo_controllo_il = models.DateTimeField(
        "Ultimo controllo servizio",
        null=True,
        blank=True,
    )
    ultimo_invio_il = models.DateTimeField("Ultimo invio automatico", null=True, blank=True)
    ultimo_invio_esito = models.CharField("Esito ultimo invio", max_length=255, blank=True)

    class Meta:
        verbose_name = "Configurazione notifiche email"
        verbose_name_plural = "Configurazioni notifiche email"

    def __str__(self):
        return "Parametri mail notifiche"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"attiva": False})
        return obj


class LogNotificaEmail(BaseModel):
    class Tipo(models.TextChoices):
        AUTOMATICA = "automatica", "Automatica"
        TEST = "test", "Test"
        MANUALE = "manuale", "Manuale"

    class Esito(models.TextChoices):
        OK = "ok", "Inviata"
        ERRORE = "errore", "Errore"
        DRY_RUN = "dry_run", "Simulazione"
        SALTATA = "saltata", "Saltata"

    inviata_il = models.DateTimeField("Data/ora invio", default=timezone.now, db_index=True)
    tipo = models.CharField(
        "Tipo",
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.AUTOMATICA,
    )
    esito = models.CharField(
        "Esito",
        max_length=20,
        choices=Esito.choices,
        default=Esito.OK,
    )
    oggetto = models.CharField("Oggetto", max_length=300)
    destinatari = models.TextField("Destinatari")
    mittente = models.CharField("Mittente", max_length=254, blank=True)
    errore = models.TextField("Errore", blank=True)
    evento = models.ForeignKey(
        EventoAgenda,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="log_notifiche",
        verbose_name="Evento",
    )
    pratica = models.ForeignKey(
        Pratica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="log_notifiche_email",
        verbose_name="Pratica",
    )

    class Meta:
        verbose_name = "Log notifica email"
        verbose_name_plural = "Log notifiche email"
        ordering = ["-inviata_il", "-id"]

    def __str__(self):
        return f"{self.inviata_il:%d/%m/%Y %H:%M} · {self.oggetto}"

    @property
    def destinatari_list(self):
        return [part.strip() for part in (self.destinatari or "").replace(";", ",").split(",") if part.strip()]
