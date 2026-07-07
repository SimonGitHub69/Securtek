from django.db import models

from apps.core.models import BaseModel


class Contatto(BaseModel):
    class TipoContatto(models.TextChoices):
        EMAIL = "email", "Email"
        TELEFONO = "telefono", "Telefono"
        CELLULARE = "cellulare", "Cellulare"
        PEC = "pec", "PEC"
        SITO_WEB = "sito_web", "Sito web"
        ALTRO = "altro", "Altro"

    anagrafica = models.ForeignKey(
        "anagrafiche.Anagrafica",
        on_delete=models.CASCADE,
        related_name="contatti",
        verbose_name="Anagrafica",
    )
    tipo = models.CharField(
        "Tipo",
        max_length=20,
        choices=TipoContatto.choices,
        default=TipoContatto.EMAIL,
    )
    valore = models.CharField(
        "Valore",
        max_length=255,
    )
    descrizione = models.CharField(
        "Descrizione",
        max_length=100,
        blank=True,
        help_text="Esempio: amministrazione, ufficio tecnico, referente privacy.",
    )
    principale = models.BooleanField(
        "Principale",
        default=False,
    )

    class Meta:
        verbose_name = "Contatto"
        verbose_name_plural = "Contatti"
        ordering = ["anagrafica__ragione_sociale", "-principale", "tipo", "valore"]

    def __str__(self):
        label = self.get_tipo_display()
        if self.descrizione:
            label = f"{label} {self.descrizione}"
        return f"{label}: {self.valore}"
