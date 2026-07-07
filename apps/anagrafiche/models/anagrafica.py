from django.db import models

from apps.core.models import BaseModel


class Anagrafica(BaseModel):
    ragione_sociale = models.CharField(
        "Ragione sociale",
        max_length=200,
    )

    partita_iva = models.CharField(
        "Partita IVA",
        max_length=20,
        blank=True,
    )

    codice_fiscale = models.CharField(
        "Codice Fiscale",
        max_length=20,
        blank=True,
    )

    email = models.EmailField(blank=True)

    telefono = models.CharField(
        max_length=30,
        blank=True,
    )

    class Meta:
        verbose_name = "Anagrafica"
        verbose_name_plural = "Anagrafiche"
        ordering = ["ragione_sociale"]

    def __str__(self):
        return self.ragione_sociale