from django.db import models
from django.core.validators import FileExtensionValidator

from apps.core.models import BaseModel


def anagrafica_logo_upload_to(instance, filename):
    return f"anagrafiche/{instance.uuid}/logo/{filename}"


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

    logo = models.FileField(
        "Logo",
        upload_to=anagrafica_logo_upload_to,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["png", "jpg", "jpeg", "webp", "svg"],
            )
        ],
    )

    class Meta:
        verbose_name = "Anagrafica"
        verbose_name_plural = "Anagrafiche"
        ordering = ["ragione_sociale"]

    def __str__(self):
        return self.ragione_sociale
