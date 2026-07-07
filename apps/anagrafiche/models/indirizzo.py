from django.db import models

from apps.core.models import BaseModel


class Indirizzo(BaseModel):
    class TipoIndirizzo(models.TextChoices):
        SEDE_LEGALE = "sede_legale", "Sede legale"
        SEDE_OPERATIVA = "sede_operativa", "Sede operativa"
        FATTURAZIONE = "fatturazione", "Fatturazione"
        SPEDIZIONE = "spedizione", "Spedizione"
        ALTRO = "altro", "Altro"

    anagrafica = models.ForeignKey(
        "anagrafiche.Anagrafica",
        on_delete=models.CASCADE,
        related_name="indirizzi",
        verbose_name="Anagrafica",
    )
    tipo = models.CharField(
        "Tipo",
        max_length=30,
        choices=TipoIndirizzo.choices,
        default=TipoIndirizzo.SEDE_OPERATIVA,
    )
    indirizzo = models.CharField(
        "Indirizzo",
        max_length=255,
    )
    civico = models.CharField(
        "Civico",
        max_length=20,
        blank=True,
    )
    cap = models.CharField(
        "CAP",
        max_length=10,
        blank=True,
    )
    comune = models.CharField(
        "Comune",
        max_length=100,
        blank=True,
    )
    provincia = models.CharField(
        "Provincia",
        max_length=2,
        blank=True,
    )
    nazione = models.CharField(
        "Nazione",
        max_length=100,
        default="Italia",
    )
    principale = models.BooleanField(
        "Principale",
        default=False,
    )

    class Meta:
        verbose_name = "Indirizzo"
        verbose_name_plural = "Indirizzi"
        ordering = ["anagrafica__ragione_sociale", "-principale", "tipo"]

    def __str__(self):
        parts = [self.indirizzo]
        if self.civico:
            parts.append(self.civico)
        location = " ".join(parts)
        city_parts = [value for value in [self.cap, self.comune, self.provincia] if value]
        if city_parts:
            location = f"{location}, {' '.join(city_parts)}"
        return location
