from django.db import models

from apps.core.models import BaseModel


class Provincia(BaseModel):
    sigla = models.CharField("Sigla", max_length=2, unique=True)
    denominazione = models.CharField("Denominazione", max_length=100)
    codice = models.CharField("Codice ISTAT", max_length=3, blank=True)
    regione = models.CharField("Regione", max_length=100, blank=True)

    class Meta:
        verbose_name = "Provincia"
        verbose_name_plural = "Province"
        ordering = ["denominazione"]

    def __str__(self):
        return f"{self.denominazione} ({self.sigla})"

    def save(self, *args, **kwargs):
        if self.sigla:
            self.sigla = self.sigla.strip().upper()
        super().save(*args, **kwargs)


class Comune(BaseModel):
    denominazione = models.CharField("Denominazione", max_length=150)
    codice_istat = models.CharField("Codice ISTAT", max_length=6, unique=True)
    codice_catastale = models.CharField("Codice catastale", max_length=4, blank=True)
    provincia = models.ForeignKey(
        Provincia,
        on_delete=models.PROTECT,
        related_name="comuni",
        verbose_name="Provincia",
    )
    cap = models.CharField("CAP", max_length=10, blank=True)
    popolazione = models.PositiveIntegerField("Popolazione", null=True, blank=True)

    class Meta:
        verbose_name = "Comune"
        verbose_name_plural = "Comuni"
        ordering = ["denominazione", "provincia__sigla"]
        indexes = [
            models.Index(fields=["denominazione"]),
            models.Index(fields=["provincia", "denominazione"]),
        ]

    def __str__(self):
        return f"{self.denominazione} ({self.provincia.sigla})"
