from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utente personalizzato SecurTek.
    Per ora eredita semplicemente da AbstractUser.
    Nei prossimi sprint aggiungeremo nuovi campi.
    """

    class Meta:
        verbose_name = "Utente"
        verbose_name_plural = "Utenti"

    def __str__(self):
        return self.get_full_name() or self.username