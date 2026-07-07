from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creato il")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modificato il")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name="Creato da",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        verbose_name="Modificato da",
    )

    is_active = models.BooleanField(default=True, verbose_name="Attivo")

    class Meta:
        abstract = True


class Indirizzo(BaseModel):
    TIPO_CHOICES = [
        ("SEDE", "Sede"),
        ("LEGALE", "Sede legale"),
        ("OPERATIVA", "Sede operativa"),
        ("RESIDENZA", "Residenza"),
        ("DOMICILIO", "Domicilio"),
        ("ALTRO", "Altro"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="SEDE")
    descrizione = models.CharField(max_length=100, blank=True)

    indirizzo = models.CharField(max_length=255)
    civico = models.CharField(max_length=20, blank=True)
    cap = models.CharField(max_length=10, blank=True)
    comune = models.CharField(max_length=100)
    provincia = models.CharField(max_length=2, blank=True)
    regione = models.CharField(max_length=100, blank=True)
    nazione = models.CharField(max_length=100, default="Italia")

    principale = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Indirizzo"
        verbose_name_plural = "Indirizzi"
        ordering = ["comune", "indirizzo"]

    def __str__(self):
        return f"{self.indirizzo} {self.civico}, {self.comune}"


class Contatto(BaseModel):
    TIPO_CHOICES = [
        ("PERSONA", "Persona"),
        ("UFFICIO", "Ufficio"),
        ("TECNICO", "Tecnico"),
        ("AMMINISTRATIVO", "Amministrativo"),
        ("COMMERCIALE", "Commerciale"),
        ("ALTRO", "Altro"),
    ]

    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, default="PERSONA")

    nome = models.CharField(max_length=100)
    cognome = models.CharField(max_length=100, blank=True)
    ruolo = models.CharField(max_length=100, blank=True)

    telefono = models.CharField(max_length=50, blank=True)
    cellulare = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    pec = models.EmailField(blank=True)

    indirizzo = models.ForeignKey(
        Indirizzo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contatti",
    )

    note = models.TextField(blank=True)
    principale = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Contatto"
        verbose_name_plural = "Contatti"
        ordering = ["cognome", "nome"]

    def __str__(self):
        if self.cognome:
            return f"{self.cognome} {self.nome}"
        return self.nome