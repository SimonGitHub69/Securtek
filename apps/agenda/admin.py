from django.contrib import admin

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda, LogNotificaEmail


@admin.register(EventoAgenda)
class EventoAgendaAdmin(admin.ModelAdmin):
    list_display = (
        "titolo",
        "tipo",
        "pratica",
        "data_inizio",
        "data_fine",
        "giorni_preavviso",
        "stato",
        "notifica_email",
        "notificato_il",
        "is_active",
    )
    readonly_fields = ("notificato_il",)
    search_fields = ("titolo", "pratica__codice", "pratica__titolo", "descrizione", "tecnici__nome", "tecnici__cognome")
    list_filter = ("tipo", "stato", "is_active", "data_inizio")
    autocomplete_fields = ("pratica",)
    filter_horizontal = ("tecnici",)


@admin.register(ConfigurazioneNotificaEmail)
class ConfigurazioneNotificaEmailAdmin(admin.ModelAdmin):
    list_display = (
        "attiva",
        "servizio_attivo",
        "intervallo_controllo_minuti",
        "host",
        "porta",
        "mittente",
        "giorni_preavviso",
        "ora_invio",
        "ultimo_controllo_il",
        "is_active",
    )


@admin.register(LogNotificaEmail)
class LogNotificaEmailAdmin(admin.ModelAdmin):
    list_display = ("inviata_il", "oggetto", "esito", "tipo", "pratica", "evento")
    list_filter = ("esito", "tipo", "inviata_il")
    search_fields = ("oggetto", "destinatari", "pratica__codice", "errore")
    readonly_fields = ("inviata_il", "created_at", "updated_at")
