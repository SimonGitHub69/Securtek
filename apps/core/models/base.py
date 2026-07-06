import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creato il",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Modificato il",
    )

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

    is_active = models.BooleanField(
        default=True,
        verbose_name="Attivo",
    )

    class Meta:
        abstract = True