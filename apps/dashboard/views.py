from django.views.generic import TemplateView
from django.conf import settings
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from apps.anagrafiche.models import Anagrafica
from apps.agenda.models import EventoAgenda
from apps.pratiche.models import (
    CategoriaPratica,
    ComunicazionePratica,
    IncaricoTecnico,
    MacroCategoriaPratica,
    Pratica,
    PraticaCategoriaAllegato,
    PraticaCategoria,
    StudioTecnico,
    TemplatePratica,
)

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".doc",
    ".docx",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".txt",
    ".xls",
    ".xlsm",
    ".xlsx",
}

NATIVE_OPEN_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".xlsm"}


def file_datetime(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())


def file_type_label(file_name):
    extension = Path(file_name or "").suffix.upper().lstrip(".")
    return extension or "-"


def office_file_priority(file_name):
    return 0 if Path(file_name or "").suffix.lower() in NATIVE_OPEN_EXTENSIONS else 1


def scan_folder_documents(q=""):
    documents = []
    query = q.lower()
    collegamenti = (
        PraticaCategoria.objects.filter(
            is_active=True,
            pratica__is_active=True,
        )
        .exclude(cartella="")
        .select_related("pratica", "categoria", "macro_categoria")
        .prefetch_related("file_metadati")
    )

    for collegamento in collegamenti:
        cartella = (collegamento.cartella or "").strip()

        if not cartella.lower().startswith(("http://", "https://")):
            folder_path = Path(cartella).expanduser()
        else:
            continue

        if not folder_path.exists() or not folder_path.is_dir():
            continue

        metadata_by_path = {
            metadata.percorso_relativo: metadata
            for metadata in collegamento.file_metadati.filter(is_active=True)
        }

        try:
            files = sorted(folder_path.rglob("*"), key=lambda item: str(item.relative_to(folder_path)).lower())
        except OSError:
            continue

        for file_path in files:
            if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
                continue

            relative_name = file_path.relative_to(folder_path).as_posix()
            metadata = metadata_by_path.get(relative_name)
            description = metadata.descrizione if metadata else ""
            pratica = collegamento.pratica
            searchable = " ".join(
                [
                    relative_name,
                    description,
                    pratica.codice,
                    pratica.titolo,
                    collegamento.categoria.denominazione,
                    collegamento.macro_categoria.denominazione if collegamento.macro_categoria else "",
                ]
            ).lower()

            if query and query not in searchable:
                continue

            try:
                stat = file_path.stat()
            except OSError:
                continue

            documents.append(
                {
                    "name": relative_name,
                    "description": description,
                    "type": file_type_label(relative_name),
                    "source": "Cartella categoria",
                    "category": collegamento.categoria.denominazione,
                    "macro": collegamento.macro_categoria.denominazione if collegamento.macro_categoria else "",
                    "pratica": pratica,
                    "updated_at": file_datetime(stat.st_mtime),
                    "open_url": reverse(
                        "pratiche:pratica_categoria_file",
                        kwargs={"pratica_pk": pratica.pk, "pk": collegamento.pk},
                    ) + f"?file={quote(relative_name)}",
                    "open_app_url": (
                        reverse(
                            "pratiche:pratica_categoria_file_open",
                            kwargs={"pratica_pk": pratica.pk, "pk": collegamento.pk},
                        ) + f"?file={quote(relative_name)}&next={quote('/documenti/')}"
                        if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS
                        else ""
                    ),
                    "detail_url": reverse("pratiche:pratica_detail", kwargs={"pk": pratica.pk}),
                    "icon": "ti-folder",
                }
            )

    return documents


def scan_uploaded_category_documents(q=""):
    documents = []
    query = q.lower()
    allegati = (
        PraticaCategoriaAllegato.objects.filter(
            is_active=True,
            pratica_categoria__is_active=True,
            pratica_categoria__pratica__is_active=True,
        )
        .select_related(
            "pratica_categoria__pratica",
            "pratica_categoria__categoria",
            "pratica_categoria__macro_categoria",
        )
        .order_by("file")
    )

    for allegato in allegati:
        pratica_categoria = allegato.pratica_categoria
        pratica = pratica_categoria.pratica
        file_name = allegato.file_nome
        searchable = " ".join(
            [
                file_name,
                allegato.descrizione,
                pratica.codice,
                pratica.titolo,
                pratica_categoria.categoria.denominazione,
                pratica_categoria.macro_categoria.denominazione if pratica_categoria.macro_categoria else "",
            ]
        ).lower()

        if query and query not in searchable:
            continue

        documents.append(
            {
                "name": file_name,
                "description": allegato.descrizione,
                "type": file_type_label(file_name),
                "source": "File singolo",
                "category": pratica_categoria.categoria.denominazione,
                "macro": pratica_categoria.macro_categoria.denominazione if pratica_categoria.macro_categoria else "",
                "pratica": pratica,
                "updated_at": allegato.updated_at,
                "open_url": reverse(
                    "pratiche:pratica_categoria_allegato_file",
                    kwargs={
                        "pratica_pk": pratica.pk,
                        "categoria_pk": pratica_categoria.pk,
                        "pk": allegato.pk,
                    },
                ),
                "open_app_url": (
                    reverse(
                        "pratiche:pratica_categoria_allegato_open",
                        kwargs={
                            "pratica_pk": pratica.pk,
                            "categoria_pk": pratica_categoria.pk,
                            "pk": allegato.pk,
                        },
                    ) + f"?next={quote('/documenti/')}"
                    if Path(file_name).suffix.lower() in NATIVE_OPEN_EXTENSIONS
                    else ""
                ),
                "detail_url": reverse("pratiche:pratica_detail", kwargs={"pk": pratica.pk}),
                "icon": "ti-paperclip",
            }
        )

    return documents


def count_linked_documents():
    categoria_files = len(scan_folder_documents())
    allegati_singoli = PraticaCategoriaAllegato.objects.filter(
        is_active=True,
        pratica_categoria__is_active=True,
        pratica_categoria__pratica__is_active=True,
    ).count()
    comunicazioni = ComunicazionePratica.objects.filter(
        is_active=True,
        allegato__gt="",
        pratica__is_active=True,
    ).count()

    return categoria_files + allegati_singoli + comunicazioni


def count_agenda_items():
    stati_finali = [
        Pratica.Stato.COMPLETATA,
        Pratica.Stato.ANNULLATA,
        Pratica.Stato.ARCHIVIATA,
    ]

    eventi_agenda = (
        EventoAgenda.objects.filter(
            is_active=True,
            pratica__is_active=True,
        )
        .exclude(stato__in=[EventoAgenda.Stato.COMPLETATO, EventoAgenda.Stato.ANNULLATO])
        .exclude(pratica__stato__in=stati_finali)
        .count()
    )
    scadenze_pratiche = (
        Pratica.objects.filter(is_active=True, data_scadenza__isnull=False)
        .exclude(stato__in=stati_finali)
        .count()
    )

    return eventi_agenda + scadenze_pratiche


class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        anagrafiche = Anagrafica.objects.filter(is_active=True)
        pratiche = Pratica.objects.filter(is_active=True).exclude(stato=Pratica.Stato.ARCHIVIATA)

        context["kpi"] = {
            "anagrafiche": anagrafiche.count(),
            "clienti": anagrafiche.count(),
            "pratiche": pratiche.count(),
            "documenti": count_linked_documents(),
            "scadenze": count_agenda_items(),
        }
        context["ultime_anagrafiche"] = anagrafiche.order_by("-created_at")[:5]

        return context


class DocumentiView(TemplateView):
    template_name = "dashboard/documenti.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = (self.request.GET.get("q") or "").strip()

        categoria_documents = scan_folder_documents(q)
        allegati_documents = scan_uploaded_category_documents(q)
        comunicazioni = (
            ComunicazionePratica.objects.filter(
                is_active=True,
                allegato__gt="",
                pratica__is_active=True,
            )
            .select_related("pratica")
            .order_by("-data_ora", "-id")
        )

        if q:
            comunicazioni = comunicazioni.filter(
                descrizione__icontains=q
            ) | comunicazioni.filter(
                allegato__icontains=q
            ) | comunicazioni.filter(
                pratica__codice__icontains=q
            ) | comunicazioni.filter(
                pratica__titolo__icontains=q
            )

        documents = []
        documents.extend(categoria_documents)
        documents.extend(allegati_documents)

        for item in comunicazioni[:100]:
            document_name = item.allegato_nome
            documents.append(
                {
                    "name": document_name,
                    "description": item.descrizione,
                    "type": file_type_label(document_name),
                    "source": "Comunicazione",
                    "category": "",
                    "macro": "",
                    "pratica": item.pratica,
                    "updated_at": item.updated_at,
                    "open_url": reverse(
                        "pratiche:comunicazione_preview" if document_name.lower().endswith(".eml") else "pratiche:comunicazione_file",
                        kwargs={"pratica_pk": item.pratica_id, "pk": item.pk},
                    ),
                    "open_app_url": "",
                    "detail_url": reverse("pratiche:pratica_detail", kwargs={"pk": item.pratica_id}),
                    "icon": "ti-mail",
                }
            )

        documents.sort(key=lambda item: (office_file_priority(item["name"]), -item["updated_at"].timestamp(), item["name"].lower()))
        context["documents"] = documents
        context["q"] = q
        context["document_counts"] = {
            "cartelle": len(categoria_documents),
            "singoli": len(allegati_documents),
            "comunicazioni": comunicazioni.count(),
            "totale": len(categoria_documents) + len(allegati_documents) + comunicazioni.count(),
        }

        return context


class SistemaView(TemplateView):
    template_name = "dashboard/sistema.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        media_root = str(getattr(settings, "MEDIA_ROOT", ""))

        context["system_status"] = [
            {
                "label": "Ambiente",
                "value": "Sviluppo" if settings.DEBUG else "Produzione",
                "icon": "ti-code",
            },
            {
                "label": "Database",
                "value": connection.vendor.upper(),
                "icon": "ti-database",
            },
            {
                "label": "Media",
                "value": media_root or "Non configurato",
                "icon": "ti-folder-cog",
            },
            {
                "label": "Fuso orario",
                "value": settings.TIME_ZONE,
                "icon": "ti-clock-cog",
            },
        ]
        context["registry_counts"] = [
            {"label": "Categorie", "value": CategoriaPratica.objects.filter(is_active=True).count()},
            {"label": "Macro-categorie", "value": MacroCategoriaPratica.objects.filter(is_active=True).count()},
            {"label": "Template pratiche", "value": TemplatePratica.objects.filter(is_active=True).count()},
            {"label": "Studi tecnici", "value": StudioTecnico.objects.filter(is_active=True).count()},
            {"label": "Incarichi", "value": IncaricoTecnico.objects.filter(is_active=True).count()},
        ]
        context["system_links"] = [
            {
                "label": "Admin Django",
                "description": "Gestione tecnica avanzata dei dati.",
                "url": reverse("admin:index"),
                "icon": "ti-shield-cog",
            },
            {
                "label": "Parametri mail",
                "description": "Configurazione notifiche per scadenze e agenda.",
                "url": reverse("agenda:configurazione_email"),
                "icon": "ti-mail-cog",
            },
            {
                "label": "Template pratiche",
                "description": "Categorie automatiche per tipologia pratica.",
                "url": reverse("pratiche:template_pratica_list"),
                "icon": "ti-template",
            },
        ]

        return context
