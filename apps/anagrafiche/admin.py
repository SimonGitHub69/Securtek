from django.contrib import admin

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo


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
        "cap",
        "comune",
        "provincia",
        "nazione",
        "principale",
        "is_active",
    )


@admin.register(Anagrafica)
class AnagraficaAdmin(admin.ModelAdmin):
    list_display = ("ragione_sociale", "partita_iva", "codice_fiscale", "email", "telefono", "logo", "is_active")
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
    search_fields = ("anagrafica__ragione_sociale", "indirizzo", "comune", "provincia", "cap")
    list_filter = ("tipo", "principale", "is_active", "provincia")
