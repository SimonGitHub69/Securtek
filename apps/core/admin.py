from django.contrib import admin
from .models import Azienda


@admin.register(Azienda)
class AziendaAdmin(admin.ModelAdmin):
    list_display = (
        "ragione_sociale",
        "partita_iva",
        "codice_fiscale",
        "email",
        "telefono",
        "is_active",
    )

    search_fields = (
        "ragione_sociale",
        "partita_iva",
        "codice_fiscale",
        "email",
    )

    list_filter = (
        "is_active",
    )