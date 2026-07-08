from django.contrib import admin

from apps.pratiche.models import (
    CategoriaPratica,
    ComunicazionePratica,
    IncaricoTecnico,
    MacroCategoriaPratica,
    Pratica,
    PraticaCategoriaAllegato,
    PraticaCategoria,
    PraticaCategoriaFile,
    PraticaMacroCategoria,
    StudioTecnico,
    Tecnico,
    TemplatePratica,
)


@admin.register(CategoriaPratica)
class CategoriaPraticaAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "is_active")
    search_fields = ("denominazione", "descrizione")
    list_filter = ("is_active",)


@admin.register(MacroCategoriaPratica)
class MacroCategoriaPraticaAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "categorie_display", "is_active")
    search_fields = ("denominazione", "descrizione", "categorie__denominazione")
    list_filter = ("is_active",)
    filter_horizontal = ("categorie",)

    @admin.display(description="Categorie")
    def categorie_display(self, obj):
        return ", ".join(obj.categorie.filter(is_active=True).values_list("denominazione", flat=True)) or "-"


@admin.register(TemplatePratica)
class TemplatePraticaAdmin(admin.ModelAdmin):
    list_display = ("tipologia", "macro_categorie_display", "categorie_display", "is_active")
    list_filter = ("tipologia", "is_active")
    filter_horizontal = ("macro_categorie", "categorie")

    @admin.display(description="Macro-categorie")
    def macro_categorie_display(self, obj):
        return ", ".join(obj.macro_categorie.filter(is_active=True).values_list("denominazione", flat=True)) or "-"

    @admin.display(description="Categorie singole")
    def categorie_display(self, obj):
        return ", ".join(obj.categorie.filter(is_active=True).values_list("denominazione", flat=True)) or "-"


@admin.register(IncaricoTecnico)
class IncaricoTecnicoAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "is_active")
    search_fields = ("denominazione", "descrizione")
    list_filter = ("is_active",)


@admin.register(StudioTecnico)
class StudioTecnicoAdmin(admin.ModelAdmin):
    list_display = ("denominazione", "email", "telefono", "is_active")
    search_fields = ("denominazione", "email", "telefono")
    list_filter = ("is_active",)


class TecnicoInline(admin.TabularInline):
    model = Tecnico
    extra = 0
    fields = ("nome", "cognome", "studio_appartenenza", "incarico", "email", "telefono", "is_active")


class PraticaCategoriaInline(admin.TabularInline):
    model = PraticaCategoria
    extra = 0
    fields = ("macro_categoria", "categoria", "cartella", "versione", "is_active")


class PraticaMacroCategoriaInline(admin.TabularInline):
    model = PraticaMacroCategoria
    extra = 0
    fields = ("macro_categoria", "is_active")


@admin.register(Pratica)
class PraticaAdmin(admin.ModelAdmin):
    list_display = ("codice", "titolo", "cliente", "categorie_display", "stato", "priorita", "data_scadenza", "is_active")
    search_fields = ("codice", "titolo", "cliente__ragione_sociale", "categoria_collegamenti__categoria__denominazione")
    list_filter = ("stato", "priorita", "categoria_collegamenti__categoria", "is_active")
    autocomplete_fields = ("cliente", "responsabile")
    inlines = (PraticaMacroCategoriaInline, PraticaCategoriaInline, TecnicoInline)

    @admin.display(description="Categorie")
    def categorie_display(self, obj):
        return ", ".join(
            obj.categoria_collegamenti.filter(is_active=True).values_list("categoria__denominazione", flat=True)
        ) or "-"


@admin.register(PraticaCategoria)
class PraticaCategoriaAdmin(admin.ModelAdmin):
    list_display = ("pratica", "macro_categoria", "categoria", "versione", "cartella", "is_active")
    search_fields = (
        "pratica__codice",
        "pratica__titolo",
        "macro_categoria__denominazione",
        "categoria__denominazione",
        "versione",
        "cartella",
    )
    list_filter = ("macro_categoria", "categoria", "is_active")


@admin.register(PraticaCategoriaFile)
class PraticaCategoriaFileAdmin(admin.ModelAdmin):
    list_display = ("pratica_categoria", "percorso_relativo", "descrizione", "is_active")
    search_fields = ("pratica_categoria__pratica__codice", "percorso_relativo", "descrizione")
    list_filter = ("is_active",)


@admin.register(PraticaCategoriaAllegato)
class PraticaCategoriaAllegatoAdmin(admin.ModelAdmin):
    list_display = ("pratica_categoria", "file", "descrizione", "is_active")
    search_fields = ("pratica_categoria__pratica__codice", "file", "descrizione")
    list_filter = ("is_active",)


@admin.register(ComunicazionePratica)
class ComunicazionePraticaAdmin(admin.ModelAdmin):
    list_display = ("pratica", "data_ora", "descrizione", "allegato", "is_active")
    search_fields = ("pratica__codice", "pratica__titolo", "descrizione", "allegato")
    list_filter = ("is_active", "data_ora")


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "cognome",
        "studio_appartenenza",
        "incarico",
        "pratica",
        "email",
        "telefono",
        "is_active",
    )
    search_fields = (
        "nome",
        "cognome",
        "studio_appartenenza__denominazione",
        "incarico__denominazione",
        "email",
        "telefono",
        "pratica__codice",
        "pratica__titolo",
    )
    list_filter = ("is_active",)
