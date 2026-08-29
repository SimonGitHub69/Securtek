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
    provincia = models.ForeignKey(
        "anagrafiche.Provincia",
        on_delete=models.PROTECT,
        related_name="indirizzi",
        verbose_name="Provincia",
        null=True,
        blank=True,
    )
    comune = models.ForeignKey(
        "anagrafiche.Comune",
        on_delete=models.PROTECT,
        related_name="indirizzi",
        verbose_name="Comune",
        null=True,
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
        city_parts = []
        if self.cap:
            city_parts.append(self.cap)
        if self.comune_id:
            city_parts.append(self.comune.denominazione)
        if self.provincia_id:
            city_parts.append(self.provincia.sigla)
        if city_parts:
            location = f"{location}, {' '.join(city_parts)}"
        return location

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.comune_id and self.provincia_id and self.comune.provincia_id != self.provincia_id:
            raise ValidationError({"comune": "Il comune non appartiene alla provincia selezionata."})

        if self.comune_id and not self.provincia_id:
            self.provincia_id = self.comune.provincia_id
