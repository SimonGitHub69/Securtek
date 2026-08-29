from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .base import BaseModel


class StampanteRilevata(BaseModel):
    descrizione = models.TextField("Descrizione", blank=True)
    gap_busta_superiore = models.DecimalField(
        "Gap busta superiore",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    gap_busta_inferiore = models.DecimalField(
        "Gap busta inferiore",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "Stampante rilevata"
        verbose_name_plural = "Stampanti rilevate"
        ordering = ["descrizione", "id"]

    def __str__(self):
        testo = (self.descrizione or "").strip()
        return testo or f"Stampante #{self.pk}"
