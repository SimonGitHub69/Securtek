from django.contrib import admin

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda


@admin.register(EventoAgenda)
class EventoAgendaAdmin(admin.ModelAdmin):
    list_display = ("titolo", "tipo", "pratica", "data_inizio", "data_fine", "giorni_preavviso", "stato", "notifica_email", "is_active")
    search_fields = ("titolo", "pratica__codice", "pratica__titolo", "descrizione", "tecnici__nome", "tecnici__cognome")
    list_filter = ("tipo", "stato", "is_active", "data_inizio")
    autocomplete_fields = ("pratica",)
    filter_horizontal = ("tecnici",)


@admin.register(ConfigurazioneNotificaEmail)
class ConfigurazioneNotificaEmailAdmin(admin.ModelAdmin):
    list_display = ("attiva", "host", "porta", "mittente", "giorni_preavviso", "is_active")
