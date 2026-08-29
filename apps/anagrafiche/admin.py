from django.contrib import admin

from apps.anagrafiche.models import Anagrafica, Comune, Contatto, Indirizzo, Provincia


class ContattoInline(admin.TabularInline):
    model = Contatto
    extra = 0
    fields = ("tipo", "valore", "descrizione", "principale", "is_active")


class IndirizzoInline(admin.TabularInline):
    model = Indirizzo
    extra = 0
    fields = (
        "tipo",
        "indirizzo",
        "civico",
        "provincia",
        "comune",
        "cap",
        "nazione",
        "principale",
        "is_active",
    )
    autocomplete_fields = ("provincia", "comune")


@admin.register(Anagrafica)
class AnagraficaAdmin(admin.ModelAdmin):
    list_display = ("ragione_sociale", "partita_iva", "codice_fiscale", "email", "telefono", "is_active")
    search_fields = ("ragione_sociale", "partita_iva", "codice_fiscale", "email", "telefono")
    list_filter = ("is_active",)
    inlines = (ContattoInline, IndirizzoInline)


@admin.register(Contatto)
class ContattoAdmin(admin.ModelAdmin):
    list_display = ("anagrafica", "tipo", "valore", "descrizione", "principale", "is_active")
    search_fields = ("anagrafica__ragione_sociale", "valore", "descrizione")
    list_filter = ("tipo", "principale", "is_active")


@admin.register(Indirizzo)
class IndirizzoAdmin(admin.ModelAdmin):
    list_display = ("anagrafica", "tipo", "indirizzo", "comune", "provincia", "principale", "is_active")
    search_fields = (
        "anagrafica__ragione_sociale",
        "indirizzo",
        "comune__denominazione",
        "provincia__sigla",
        "provincia__denominazione",
        "cap",
    )
    list_filter = ("tipo", "principale", "is_active", "provincia")
    autocomplete_fields = ("anagrafica", "provincia", "comune")


@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "sigla", "regione", "codice", "is_active")
    search_fields = ("denominazione", "sigla", "regione", "codice")
    list_filter = ("regione", "is_active")


@admin.register(Comune)
class ComuneAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "provincia", "cap", "codice_istat", "is_active")
    search_fields = ("denominazione", "cap", "codice_istat", "codice_catastale", "provincia__sigla")
    list_filter = ("provincia", "is_active")
    autocomplete_fields = ("provincia",)