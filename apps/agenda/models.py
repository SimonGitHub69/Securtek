from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.pratiche.models import Pratica


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
    notificato_il = models.DateTimeField("Notificato il", null=True, blank=True)
    descrizione = models.TextField("Descrizione", blank=True)

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
    username = models.CharField("Username", max_length=200, blank=True)
    password = models.CharField("Password", max_length=200, blank=True)
    mittente = models.EmailField("Mittente", blank=True)
    destinatari_default = models.TextField("Destinatari predefiniti", blank=True)
    giorni_preavviso = models.PositiveSmallIntegerField("Giorni preavviso", default=7)

    class Meta:
        verbose_name = "Configurazione notifiche email"
        verbose_name_plural = "Configurazioni notifiche email"

    def __str__(self):
        return "Parametri mail notifiche"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"attiva": False})
        return obj
