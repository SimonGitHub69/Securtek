from django.contrib import admin

from apps.core.models import StampanteRilevata


@admin.register(StampanteRilevata)
class StampanteRilevataAdmin(admin.ModelAdmin):
    list_display = (
        "descrizione",
        "gap_busta_superiore",
        "gap_busta_inferiore",
        "is_active",
        "updated_at",
    )
    search_fields = ("descrizione", "note")
    list_filter = ("is_active",)
    readonly_fields = ("uuid", "created_at", "updated_at")
