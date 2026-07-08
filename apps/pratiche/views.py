from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files import File
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View
from datetime import datetime
from email import policy
from email.parser import BytesParser
import os
from pathlib import Path
import subprocess
from urllib.parse import quote, unquote, urlparse
from urllib.parse import urlencode


def decode_email_header(message, header_name):
    value = message.get(header_name, "")
    return str(value) if value else ""


def extract_eml_preview(file_obj):
    message = BytesParser(policy=policy.default).parse(file_obj)
    plain_body = ""
    html_body = ""
    attachments = []

    for part in message.walk():
        if part.is_multipart():
            continue

        disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        filename = part.get_filename()

        if disposition == "attachment" or filename:
            attachments.append(
                {
                    "name": filename or "Allegato senza nome",
                    "content_type": content_type,
                }
            )
            continue

        if content_type == "text/plain" and not plain_body:
            plain_body = part.get_content()

        if content_type == "text/html" and not html_body:
            html_body = part.get_content()

    if not plain_body and not html_body and not message.is_multipart():
        payload = message.get_content()
        if isinstance(payload, str):
            plain_body = payload

    return {
        "subject": decode_email_header(message, "subject"),
        "from": decode_email_header(message, "from"),
        "to": decode_email_header(message, "to"),
        "cc": decode_email_header(message, "cc"),
        "date": decode_email_header(message, "date"),
        "plain_body": plain_body,
        "html_body": html_body,
        "attachments": attachments,
    }

from apps.pratiche.forms import (
    CategoriaPraticaForm,
    ComunicazionePraticaForm,
    IncaricoTecnicoForm,
    MacroCategoriaPraticaForm,
    PraticaForm,
    PraticaCategoriaAllegatoUploadForm,
    PraticaCategoriaForm,
    PraticaCategoriaFileUploadForm,
    PraticaCategoriaFormSet,
    PraticaMacroCategoriaApplyForm,
    StudioTecnicoForm,
    TecnicoForm,
    TecnicoFormSet,
    TemplatePraticaForm,
)
from apps.agenda.models import EventoAgenda
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


SUPPORTED_FOLDER_EXTENSIONS = {
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


def office_file_priority(file_path):
    return 0 if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS else 1


def open_with_default_application(file_path):
    if os.name == "nt":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(file_path)], shell=False)
            return
        except OSError:
            pass

    os.startfile(str(file_path))


def is_external_link(value):
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def format_file_datetime(timestamp):
    value = datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())
    return value.strftime("%d/%m/%Y %H:%M")


def get_pratica_categoria_or_404(pratica_pk, pk):
    return get_object_or_404(
        PraticaCategoria,
        pk=pk,
        pratica_id=pratica_pk,
        is_active=True,
    )


def get_pratica_categoria_folder_path(pratica_categoria):
    folder_value = (pratica_categoria.cartella or "").strip()

    if not folder_value or is_external_link(folder_value):
        return None

    folder_path = Path(folder_value).expanduser().resolve()

    if not folder_path.exists() or not folder_path.is_dir():
        return None

    return folder_path


def resolve_categoria_file_path(pratica_categoria, relative_file):
    folder_path = get_pratica_categoria_folder_path(pratica_categoria)
    file_name = unquote(relative_file or "").strip()

    if not folder_path or not file_name:
        raise Http404("File non disponibile")

    file_path = (folder_path / file_name).resolve()

    if folder_path not in file_path.parents:
        raise Http404("Percorso non valido")

    if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
        raise Http404("File non disponibile")

    return folder_path, file_path


def resolve_preview_folder_file_path(folder_value, relative_file):
    folder_text = (folder_value or "").strip()
    file_name = unquote(relative_file or "").strip()

    if not folder_text or not file_name or is_external_link(folder_text):
        raise Http404("File non disponibile")

    folder_path = Path(folder_text).expanduser().resolve()

    if not folder_path.exists() or not folder_path.is_dir():
        raise Http404("Cartella non disponibile")

    file_path = (folder_path / file_name).resolve()

    if folder_path not in file_path.parents:
        raise Http404("Percorso non valido")

    if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
        raise Http404("File non disponibile")

    return folder_path, file_path


def get_pratica_categoria_allegato_or_404(pratica_pk, categoria_pk, pk):
    return get_object_or_404(
        PraticaCategoriaAllegato,
        pk=pk,
        pratica_categoria_id=categoria_pk,
        pratica_categoria__pratica_id=pratica_pk,
        is_active=True,
    )


def build_uploaded_file_entry(allegato):
    file_path = Path(allegato.file.path)

    try:
        stat = file_path.stat()
        size_kb = max(1, round(stat.st_size / 1024))
        modified_at = format_file_datetime(stat.st_mtime)
    except OSError:
        size_kb = "-"
        modified_at = "-"

    return {
        "id": allegato.pk,
        "name": allegato.file_nome,
        "description": allegato.descrizione,
        "extension": file_path.suffix.upper().lstrip(".") or "-",
        "size_kb": size_kb,
        "modified_at": modified_at,
        "open_url": reverse(
            "pratiche:pratica_categoria_allegato_file",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        ),
        "open_app_url": reverse(
            "pratiche:pratica_categoria_allegato_open",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        )
        if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS
        else "",
        "delete_url": reverse(
            "pratiche:pratica_categoria_allegato_delete",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        ),
        "destroy_url": reverse(
            "pratiche:pratica_categoria_allegato_destroy",
            kwargs={
                "pratica_pk": allegato.pratica_categoria.pratica_id,
                "categoria_pk": allegato.pratica_categoria_id,
                "pk": allegato.pk,
            },
        ),
    }


def create_category_attachment_from_path(pratica_categoria, selected_path, user=None):
    file_path = Path(selected_path).expanduser().resolve()

    if not file_path.exists() or not file_path.is_file():
        raise ValueError("File non trovato")

    if file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
        raise ValueError("Tipo file non supportato")

    allegato = PraticaCategoriaAllegato(
        pratica_categoria=pratica_categoria,
        descrizione=file_path.name,
        created_by=user,
        updated_by=user,
    )

    with file_path.open("rb") as source:
        allegato.file.save(file_path.name, File(source), save=False)

    allegato.save()
    return allegato


def get_supported_file_entries(folder_path, pratica_categoria=None):
    entries = []
    metadata_by_path = {}

    if pratica_categoria:
        metadata_by_path = {
            metadata.percorso_relativo: metadata
            for metadata in pratica_categoria.file_metadati.filter(is_active=True)
        }

    for file_path in sorted(
        folder_path.rglob("*"),
        key=lambda item: (office_file_priority(item), str(item.relative_to(folder_path)).lower()),
    ):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
            continue

        stat = file_path.stat()
        relative_path = file_path.relative_to(folder_path)
        relative_path_text = relative_path.as_posix()
        metadata = metadata_by_path.get(relative_path_text)

        if metadata and metadata.scollegato:
            continue

        url = ""
        open_app_url = ""
        preview_open_url = ""
        description_url = ""
        delete_url = ""
        unlink_url = ""

        if pratica_categoria:
            url = reverse(
                "pratiche:pratica_categoria_file",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            ) + f"?file={quote(relative_path_text)}"
            if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS:
                open_app_url = reverse(
                    "pratiche:pratica_categoria_file_open",
                    kwargs={
                        "pratica_pk": pratica_categoria.pratica_id,
                        "pk": pratica_categoria.pk,
                    },
                ) + f"?file={quote(relative_path_text)}"
            description_url = reverse(
                "pratiche:pratica_categoria_file_description",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            )
            delete_url = reverse(
                "pratiche:pratica_categoria_file_delete",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            )
            unlink_url = reverse(
                "pratiche:pratica_categoria_file_unlink",
                kwargs={
                    "pratica_pk": pratica_categoria.pratica_id,
                    "pk": pratica_categoria.pk,
                },
            )
        else:
            preview_open_url = reverse("pratiche:folder_preview_file_open") + (
                f"?path={quote(str(folder_path))}&file={quote(relative_path_text)}"
            )
            delete_url = reverse("pratiche:folder_preview_file_delete")

        entries.append(
            {
                "name": relative_path_text,
                "description": metadata.descrizione if metadata else "",
                "extension": file_path.suffix.upper().lstrip("."),
                "size_kb": max(1, round(stat.st_size / 1024)),
                "created_at": format_file_datetime(stat.st_ctime),
                "modified_at": format_file_datetime(stat.st_mtime),
                "url": url,
                "open_app_url": open_app_url,
                "preview_open_url": preview_open_url,
                "description_url": description_url,
                "delete_url": delete_url,
                "unlink_url": unlink_url,
            }
        )

    return entries


def build_folder_file_entries(pratica_categoria):
    cartella = (pratica_categoria.cartella or "").strip()

    pratica_categoria.cartella_is_link = False
    pratica_categoria.cartella_is_folder = False
    pratica_categoria.cartella_error = ""
    pratica_categoria.file_entries = []

    if not cartella:
        return

    if is_external_link(cartella):
        pratica_categoria.cartella_is_link = True
        return

    folder_path = Path(cartella).expanduser()

    if not folder_path.exists():
        pratica_categoria.cartella_error = "Cartella non trovata"
        return

    if not folder_path.is_dir():
        pratica_categoria.cartella_error = "Il percorso non è una cartella"
        return

    pratica_categoria.cartella_is_folder = True
    pratica_categoria.file_entries = get_supported_file_entries(folder_path, pratica_categoria)


def save_category_formset_attachments(request, formset):
    for form in formset.forms:
        if not hasattr(form, "cleaned_data") or not form.cleaned_data:
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        pratica_categoria = form.instance

        if not pratica_categoria.pk:
            continue

        uploaded_files = request.FILES.getlist(f"{form.prefix}-allegato_file")

        for uploaded_file in uploaded_files:
            PraticaCategoriaAllegato.objects.create(
                pratica_categoria=pratica_categoria,
                file=uploaded_file,
                descrizione=(request.POST.get(f"{form.prefix}-allegato_descrizione") or "").strip(),
                created_by=request.user,
                updated_by=request.user,
            )

        for relative_file in request.POST.getlist(f"{form.prefix}-scollega_files"):
            relative_file = (relative_file or "").strip()

            if not relative_file:
                continue

            metadata, created = PraticaCategoriaFile.objects.update_or_create(
                pratica_categoria=pratica_categoria,
                percorso_relativo=relative_file,
                is_active=True,
                defaults={
                    "scollegato": True,
                    "updated_by": request.user,
                },
            )

            if created:
                metadata.created_by = request.user
                metadata.save(update_fields=["created_by", "updated_at"])


def get_safe_next_url(request):
    next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()

    if not next_url:
        return ""

    if not next_url.startswith("/") or next_url.startswith("//"):
        return ""

    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ""

    return next_url


def with_next(url, next_url):
    if not next_url:
        return url

    return f"{url}?{urlencode({'next': next_url})}"


def apply_template_to_pratica(pratica, user=None):
    template = (
        TemplatePratica.objects.filter(tipologia=pratica.tipologia, is_active=True)
        .prefetch_related("macro_categorie__categorie", "categorie")
        .first()
    )

    if not template:
        return 0

    created_count = 0

    for macro_categoria in template.macro_categorie.filter(is_active=True):
        PraticaMacroCategoria.objects.get_or_create(
            pratica=pratica,
            macro_categoria=macro_categoria,
            is_active=True,
            defaults={"created_by": user, "updated_by": user},
        )

        for categoria in macro_categoria.categorie.filter(is_active=True):
            _, created = PraticaCategoria.objects.get_or_create(
                pratica=pratica,
                macro_categoria=macro_categoria,
                categoria=categoria,
                versione="",
                is_active=True,
                defaults={"created_by": user, "updated_by": user, "origine_template": True},
            )
            if created:
                created_count += 1

    for categoria in template.categorie.filter(is_active=True):
        _, created = PraticaCategoria.objects.get_or_create(
            pratica=pratica,
            macro_categoria=None,
            categoria=categoria,
            versione="",
            is_active=True,
            defaults={"created_by": user, "updated_by": user, "origine_template": True},
        )
        if created:
            created_count += 1

    return created_count


class PraticaListView(LoginRequiredMixin, ListView):
    model = Pratica
    template_name = "pratiche/pratica_list.html"
    context_object_name = "pratiche"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Pratica.objects.filter(is_active=True)
            .select_related("cliente", "responsabile")
            .prefetch_related(
                Prefetch(
                    "categoria_collegamenti",
                    queryset=PraticaCategoria.objects.filter(is_active=True).select_related("categoria", "macro_categoria"),
                    to_attr="categorie_attive",
                ),
                Prefetch(
                    "macro_categoria_collegamenti",
                    queryset=PraticaMacroCategoria.objects.filter(is_active=True).select_related("macro_categoria"),
                    to_attr="macro_categorie_attive",
                )
            )
        )

        q = (self.request.GET.get("q") or "").strip()
        stato = self.request.GET.get("stato") or ""
        priorita = self.request.GET.get("priorita") or ""
        categoria = self.request.GET.get("categoria") or ""

        if q:
            queryset = queryset.filter(
                Q(codice__icontains=q)
                | Q(titolo__icontains=q)
                | Q(cliente__ragione_sociale__icontains=q)
                | Q(categoria_collegamenti__categoria__denominazione__icontains=q)
                | Q(macro_categoria_collegamenti__macro_categoria__denominazione__icontains=q)
            )

        if stato:
            queryset = queryset.filter(stato=stato)

        if priorita:
            queryset = queryset.filter(priorita=priorita)

        if categoria:
            queryset = queryset.filter(categoria_collegamenti__categoria_id=categoria)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stati"] = Pratica.Stato.choices
        context["priorita"] = Pratica.Priorita.choices
        context["categorie"] = CategoriaPratica.objects.filter(is_active=True).order_by("denominazione")
        return context


class PraticaDetailView(LoginRequiredMixin, DetailView):
    model = Pratica
    template_name = "pratiche/pratica_detail.html"
    context_object_name = "pratica"
    queryset = Pratica.objects.select_related("cliente", "responsabile").prefetch_related(
        Prefetch(
            "categoria_collegamenti",
            queryset=PraticaCategoria.objects.filter(is_active=True).select_related("categoria", "macro_categoria"),
            to_attr="categorie_attive",
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tecnici"] = self.object.tecnici.filter(is_active=True)
        context["eventi_agenda"] = self.object.eventi_agenda.filter(is_active=True).order_by(
            "data_inizio",
            "ora_inizio",
        )[:8]
        context["comunicazioni"] = self.object.comunicazioni.filter(is_active=True).order_by("-data_ora", "-id")
        context["comunicazione_form"] = ComunicazionePraticaForm()
        macro_categorie_pratica = list(
            self.object.macro_categoria_collegamenti.filter(
                is_active=True
            ).select_related("macro_categoria").prefetch_related("macro_categoria__categorie")
        )
        context["macro_categorie_pratica"] = macro_categorie_pratica
        context["macro_categoria_apply_form"] = PraticaMacroCategoriaApplyForm()
        categorie_pratica = list(
            self.object.categoria_collegamenti.filter(is_active=True).select_related("categoria", "macro_categoria")
        )
        for pratica_categoria in categorie_pratica:
            build_folder_file_entries(pratica_categoria)
            pratica_categoria.allegato_entries = [
                build_uploaded_file_entry(allegato)
                for allegato in pratica_categoria.allegati_singoli.filter(is_active=True)
            ]

        context["categorie_pratica"] = categorie_pratica
        context["return_url"] = get_safe_next_url(self.request) or reverse("pratiche:pratica_list")
        context["return_label"] = "Anagrafica" if get_safe_next_url(self.request) else "Elenco"
        context["next_url"] = get_safe_next_url(self.request)
        return context


class PraticaCreateView(LoginRequiredMixin, CreateView):
    model = Pratica
    form_class = PraticaForm
    template_name = "pratiche/pratica_form.html"

    def get_initial(self):
        initial = super().get_initial()
        cliente_id = self.request.GET.get("cliente")

        if cliente_id:
            initial["cliente"] = cliente_id

        return initial

    def get_inline_formsets(self, data=None):
        pratica = self.object or Pratica()
        return {
            "categorie_formset": PraticaCategoriaFormSet(
                data=data,
                instance=pratica,
                prefix="categorie",
                queryset=PraticaCategoria.objects.none(),
            ),
            "tecnici_formset": TecnicoFormSet(
                data=data,
                instance=pratica,
                prefix="tecnici",
                queryset=Tecnico.objects.none(),
            ),
        }

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formsets = self.get_inline_formsets(data=request.POST)

        if form.is_valid() and all(formset.is_valid() for formset in formsets.values()):
            return self.forms_valid(form, formsets)

        return self.forms_invalid(form, formsets)

    def forms_valid(self, form, formsets):
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            if not form.instance.responsabile:
                form.instance.responsabile = self.request.user
            self.object = form.save()
            self.save_inline_formsets(formsets)
            if not self.object.categoria_collegamenti.filter(is_active=True).exists():
                categorie_create = apply_template_to_pratica(self.object, self.request.user)
                if categorie_create:
                    messages.info(
                        self.request,
                        f"Template pratica applicato: categorie aggiunte {categorie_create}.",
                    )

        messages.success(self.request, "Pratica creata correttamente.")
        return redirect(self.get_success_url())

    def forms_invalid(self, form, formsets):
        return self.render_to_response(self.get_context_data(form=form, **formsets))

    def save_inline_formsets(self, formsets):
        for formset in formsets.values():
            formset.instance = self.object
            instances = formset.save(commit=False)

            for deleted_object in formset.deleted_objects:
                if deleted_object.pk:
                    deleted_object.soft_delete(user=self.request.user)

            for instance in instances:
                instance.pratica = self.object
                if not instance.pk:
                    instance.created_by = self.request.user
                instance.updated_by = self.request.user
                instance.save()

            formset.save_m2m()
            if getattr(formset, "prefix", "") == "categorie":
                save_category_formset_attachments(self.request, formset)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        if not form.instance.responsabile:
            form.instance.responsabile = self.request.user
        messages.success(self.request, "Pratica creata correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        context["cancel_url"] = next_url or reverse("pratiche:pratica_list")
        if "categorie_formset" not in context or "tecnici_formset" not in context:
            context.update(self.get_inline_formsets())
        return context

    def get_success_url(self):
        update_url = reverse("pratiche:pratica_update", kwargs={"pk": self.object.pk})
        return with_next(update_url, get_safe_next_url(self.request))


class PraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = Pratica
    form_class = PraticaForm
    template_name = "pratiche/pratica_form.html"

    def get_queryset(self):
        return Pratica.objects.filter(is_active=True)

    def get_inline_formsets(self, data=None):
        return {
            "categorie_formset": PraticaCategoriaFormSet(
                data=data,
                instance=self.object,
                prefix="categorie",
                queryset=PraticaCategoria.objects.filter(is_active=True),
            ),
            "tecnici_formset": TecnicoFormSet(
                data=data,
                instance=self.object,
                prefix="tecnici",
                queryset=Tecnico.objects.filter(is_active=True),
            ),
        }

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formsets = self.get_inline_formsets(data=request.POST)

        if form.is_valid() and all(formset.is_valid() for formset in formsets.values()):
            return self.forms_valid(form, formsets)

        return self.forms_invalid(form, formsets)

    def forms_valid(self, form, formsets):
        with transaction.atomic():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            self.save_inline_formsets(formsets)

        messages.success(self.request, "Pratica aggiornata correttamente.")
        return redirect(self.get_success_url())

    def forms_invalid(self, form, formsets):
        return self.render_to_response(self.get_context_data(form=form, **formsets))

    def save_inline_formsets(self, formsets):
        for formset in formsets.values():
            instances = formset.save(commit=False)

            for deleted_object in formset.deleted_objects:
                if deleted_object.pk:
                    deleted_object.soft_delete(user=self.request.user)

            for instance in instances:
                instance.pratica = self.object
                if not instance.pk:
                    instance.created_by = self.request.user
                instance.updated_by = self.request.user
                instance.save()

            formset.save_m2m()
            if getattr(formset, "prefix", "") == "categorie":
                save_category_formset_attachments(self.request, formset)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Pratica aggiornata correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        detail_url = reverse("pratiche:pratica_detail", kwargs={"pk": self.object.pk})
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        context["cancel_url"] = with_next(detail_url, next_url)
        if "categorie_formset" not in context or "tecnici_formset" not in context:
            context.update(self.get_inline_formsets())
        return context

    def get_success_url(self):
        detail_url = reverse("pratiche:pratica_detail", kwargs={"pk": self.object.pk})
        return with_next(detail_url, get_safe_next_url(self.request))


class PraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pk"], is_active=True)
        pratica.soft_delete(user=request.user)
        messages.success(request, "Pratica eliminata correttamente.")
        return redirect("pratiche:pratica_list")


class ComunicazionePraticaCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        form = ComunicazionePraticaForm(request.POST, request.FILES)

        if form.is_valid():
            comunicazione = form.save(commit=False)
            comunicazione.pratica = pratica
            comunicazione.created_by = request.user
            comunicazione.updated_by = request.user
            comunicazione.save()
            messages.success(request, "Comunicazione registrata correttamente.")
        else:
            messages.error(request, "Controlla i dati della comunicazione.")

        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class ComunicazionePraticaFileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        comunicazione = get_object_or_404(
            ComunicazionePratica,
            pk=kwargs["pk"],
            pratica_id=kwargs["pratica_pk"],
            is_active=True,
        )

        if not comunicazione.allegato:
            raise Http404("Allegato non disponibile")

        return FileResponse(
            comunicazione.allegato.open("rb"),
            as_attachment=False,
            filename=comunicazione.allegato_nome,
        )


class ComunicazionePraticaPreviewView(LoginRequiredMixin, DetailView):
    model = ComunicazionePratica
    template_name = "pratiche/comunicazione_preview.html"
    context_object_name = "comunicazione"

    def get_queryset(self):
        return ComunicazionePratica.objects.filter(
            pratica_id=self.kwargs["pratica_pk"],
            is_active=True,
        ).select_related("pratica", "pratica__cliente")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.object.allegato:
            raise Http404("Allegato non disponibile")

        if not self.object.allegato_nome.lower().endswith(".eml"):
            return redirect("pratiche:comunicazione_file", pratica_pk=self.object.pratica_id, pk=self.object.pk)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        with self.object.allegato.open("rb") as file_obj:
            context["email_preview"] = extract_eml_preview(file_obj)

        return context


class CategoriaPraticaListView(LoginRequiredMixin, ListView):
    model = CategoriaPratica
    template_name = "pratiche/categoria_pratica_list.html"
    context_object_name = "categorie"
    paginate_by = 20

    def get_queryset(self):
        queryset = CategoriaPratica.objects.filter(is_active=True).annotate(
            pratiche_attive=Count(
                "pratica_collegamenti",
                filter=Q(pratica_collegamenti__is_active=True, pratica_collegamenti__pratica__is_active=True),
                distinct=True,
            )
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(descrizione__icontains=q)
            )

        return queryset.order_by("denominazione")


class CategoriaPraticaCreateView(LoginRequiredMixin, CreateView):
    model = CategoriaPratica
    form_class = CategoriaPraticaForm
    template_name = "pratiche/categoria_pratica_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:categoria_pratica_list")


class CategoriaPraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = CategoriaPratica
    form_class = CategoriaPraticaForm
    template_name = "pratiche/categoria_pratica_form.html"

    def get_queryset(self):
        return CategoriaPratica.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:categoria_pratica_list")


class CategoriaPraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        categoria = get_object_or_404(CategoriaPratica, pk=kwargs["pk"], is_active=True)
        categoria.soft_delete(user=request.user)
        messages.success(request, "Categoria eliminata correttamente.")
        return redirect("pratiche:categoria_pratica_list")


class MacroCategoriaPraticaListView(LoginRequiredMixin, ListView):
    model = MacroCategoriaPratica
    template_name = "pratiche/macro_categoria_pratica_list.html"
    context_object_name = "macro_categorie"
    paginate_by = 20

    def get_queryset(self):
        queryset = MacroCategoriaPratica.objects.filter(is_active=True).annotate(
            categorie_count=Count("categorie", filter=Q(categorie__is_active=True), distinct=True),
            pratiche_attive=Count(
                "pratica_collegamenti",
                filter=Q(pratica_collegamenti__is_active=True, pratica_collegamenti__pratica__is_active=True),
                distinct=True,
            ),
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(descrizione__icontains=q)
                | Q(categorie__denominazione__icontains=q)
            )

        return queryset.prefetch_related("categorie").order_by("denominazione").distinct()


class MacroCategoriaPraticaCreateView(LoginRequiredMixin, CreateView):
    model = MacroCategoriaPratica
    form_class = MacroCategoriaPraticaForm
    template_name = "pratiche/macro_categoria_pratica_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Macro-categoria creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:macro_categoria_pratica_list")


class MacroCategoriaPraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = MacroCategoriaPratica
    form_class = MacroCategoriaPraticaForm
    template_name = "pratiche/macro_categoria_pratica_form.html"

    def get_queryset(self):
        return MacroCategoriaPratica.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Macro-categoria aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:macro_categoria_pratica_list")


class MacroCategoriaPraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        macro_categoria = get_object_or_404(MacroCategoriaPratica, pk=kwargs["pk"], is_active=True)
        macro_categoria.soft_delete(user=request.user)
        messages.success(request, "Macro-categoria eliminata correttamente.")
        return redirect("pratiche:macro_categoria_pratica_list")


class PraticaMacroCategoriaApplyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        form = PraticaMacroCategoriaApplyForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Seleziona una macro-categoria valida.")
            return redirect("pratiche:pratica_detail", pk=pratica.pk)

        macro_categoria = form.cleaned_data["macro_categoria"]
        categorie = list(macro_categoria.categorie.filter(is_active=True))

        with transaction.atomic():
            collegamento, created = PraticaMacroCategoria.objects.get_or_create(
                pratica=pratica,
                macro_categoria=macro_categoria,
                is_active=True,
                defaults={
                    "created_by": request.user,
                    "updated_by": request.user,
                },
            )
            if not created:
                collegamento.updated_by = request.user
                collegamento.save(update_fields=["updated_by", "updated_at"])

            categorie_aggiunte = 0
            for categoria in categorie:
                _, categoria_created = PraticaCategoria.objects.get_or_create(
                    pratica=pratica,
                    macro_categoria=macro_categoria,
                    categoria=categoria,
                    versione="",
                    is_active=True,
                    defaults={
                        "created_by": request.user,
                        "updated_by": request.user,
                        "origine_template": False,
                    },
                )
                if categoria_created:
                    categorie_aggiunte += 1

        if categorie_aggiunte:
            messages.success(
                request,
                f"Macro-categoria collegata. Categorie aggiunte: {categorie_aggiunte}.",
            )
        else:
            messages.info(request, "Macro-categoria collegata. Le categorie erano gia' presenti nella pratica.")

        return redirect("pratiche:pratica_detail", pk=pratica.pk)


class TemplatePraticaListView(LoginRequiredMixin, ListView):
    model = TemplatePratica
    template_name = "pratiche/template_pratica_list.html"
    context_object_name = "template_pratiche"

    def get_queryset(self):
        return (
            TemplatePratica.objects.filter(is_active=True)
            .prefetch_related("macro_categorie", "categorie")
            .order_by("tipologia")
        )


class TemplatePraticaCreateView(LoginRequiredMixin, CreateView):
    model = TemplatePratica
    form_class = TemplatePraticaForm
    template_name = "pratiche/template_pratica_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Template pratica creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:template_pratica_list")


class TemplatePraticaUpdateView(LoginRequiredMixin, UpdateView):
    model = TemplatePratica
    form_class = TemplatePraticaForm
    template_name = "pratiche/template_pratica_form.html"

    def get_queryset(self):
        return TemplatePratica.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Template pratica aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:template_pratica_list")


class TemplatePraticaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        template = get_object_or_404(TemplatePratica, pk=kwargs["pk"], is_active=True)
        template.soft_delete(user=request.user)
        messages.success(request, "Template pratica eliminato correttamente.")
        return redirect("pratiche:template_pratica_list")


class TemplatePraticaRowsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        tipologia = (request.GET.get("tipologia") or "").strip()
        template = (
            TemplatePratica.objects.filter(tipologia=tipologia, is_active=True)
            .prefetch_related("macro_categorie__categorie", "categorie")
            .first()
        )

        if not template:
            return JsonResponse({"rows": []})

        rows = []

        for macro_categoria in template.macro_categorie.filter(is_active=True):
            for categoria in macro_categoria.categorie.filter(is_active=True):
                rows.append(
                    {
                        "macro_categoria": macro_categoria.pk,
                        "macro_categoria_label": macro_categoria.denominazione,
                        "categoria": categoria.pk,
                        "categoria_label": categoria.denominazione,
                    }
                )

        for categoria in template.categorie.filter(is_active=True):
            rows.append(
                {
                    "macro_categoria": "",
                    "macro_categoria_label": "",
                    "categoria": categoria.pk,
                    "categoria_label": categoria.denominazione,
                }
            )

        return JsonResponse({"rows": rows})


class PraticaCategoriaCreateView(LoginRequiredMixin, CreateView):
    model = PraticaCategoria
    form_class = PraticaCategoriaForm
    template_name = "pratiche/pratica_categoria_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pratica"] = self.pratica
        return kwargs

    def form_valid(self, form):
        form.instance.pratica = self.pratica
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria collegata correttamente.")
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(
                "versione",
                "Questa categoria e questa versione sono gia' collegate alla pratica.",
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pratica"] = self.pratica
        context["page_title"] = "Collega categoria"
        return context

    def get_success_url(self):
        return reverse_lazy("pratiche:pratica_detail", kwargs={"pk": self.pratica.pk})


class PraticaCategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = PraticaCategoria
    form_class = PraticaCategoriaForm
    template_name = "pratiche/pratica_categoria_form.html"

    def get_queryset(self):
        return PraticaCategoria.objects.filter(pratica_id=self.kwargs["pratica_pk"], is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pratica"] = self.object.pratica
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Categoria aggiornata correttamente.")
        try:
            return super().form_valid(form)
        except IntegrityError:
            form.add_error(
                "versione",
                "Questa categoria e questa versione sono gia' collegate alla pratica.",
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pratica"] = self.object.pratica
        context["page_title"] = "Modifica categoria pratica"
        return context

    def get_success_url(self):
        return reverse_lazy("pratiche:pratica_detail", kwargs={"pk": self.object.pratica_id})


class PraticaCategoriaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_object_or_404(
            PraticaCategoria,
            pk=kwargs["pk"],
            pratica_id=kwargs["pratica_pk"],
            is_active=True,
        )
        pratica_pk = pratica_categoria.pratica_id
        pratica_categoria.soft_delete(user=request.user)
        messages.success(request, "Categoria rimossa dalla pratica.")
        return redirect("pratiche:pratica_detail", pk=pratica_pk)


class PraticaCategoriaFileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        _, file_path = resolve_categoria_file_path(pratica_categoria, request.GET.get("file") or "")

        return FileResponse(file_path.open("rb"), as_attachment=False, filename=file_path.name)


class PraticaCategoriaFileOpenView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        _, file_path = resolve_categoria_file_path(pratica_categoria, request.GET.get("file") or "")
        return_url = get_safe_next_url(request) or (
            reverse("pratiche:pratica_detail", kwargs={"pk": pratica_categoria.pratica_id})
            + f"#category-detail-{pratica_categoria.pk}"
        )

        if file_path.suffix.lower() not in NATIVE_OPEN_EXTENSIONS:
            return redirect(return_url)

        try:
            open_with_default_application(file_path)
            messages.success(request, f"File aperto: {file_path.name}")
        except OSError as exc:
            messages.error(request, f"Impossibile aprire il file con l'applicazione originale: {exc}")

        return redirect(return_url)


class PraticaCategoriaFileUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        folder_path = get_pratica_categoria_folder_path(pratica_categoria)

        if not folder_path:
            messages.error(request, "Collega prima una cartella valida alla categoria.")
            return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])

        uploaded_files = request.FILES.getlist("file")
        description = (request.POST.get("descrizione") or "").strip()

        if not uploaded_files:
            messages.error(request, "Seleziona un file valido da aggiungere.")
            return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])

        added_count = 0

        for uploaded_file in uploaded_files:
            file_name = Path(uploaded_file.name).name

            if not file_name:
                messages.error(request, "Nome file non valido.")
                continue

            target_path = (folder_path / file_name).resolve()

            if folder_path not in target_path.parents:
                messages.error(request, f"Percorso file non valido: {file_name}")
                continue

            if target_path.suffix.lower() not in SUPPORTED_FOLDER_EXTENSIONS:
                messages.error(request, f"Tipo file non supportato: {file_name}")
                continue

            if target_path.exists():
                messages.error(request, f"Esiste gia' un file con questo nome nella cartella: {file_name}")
                continue

            with target_path.open("wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            PraticaCategoriaFile.objects.update_or_create(
                pratica_categoria=pratica_categoria,
                percorso_relativo=file_name,
                is_active=True,
                defaults={
                    "descrizione": description,
                    "scollegato": False,
                    "created_by": request.user,
                    "updated_by": request.user,
                },
            )
            added_count += 1

        if added_count:
            messages.success(request, f"{added_count} file aggiunti correttamente.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaFileDescriptionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        relative_file = (request.POST.get("file") or "").strip()

        resolve_categoria_file_path(pratica_categoria, relative_file)

        metadata, created = PraticaCategoriaFile.objects.update_or_create(
            pratica_categoria=pratica_categoria,
            percorso_relativo=relative_file,
            is_active=True,
            defaults={
                "descrizione": (request.POST.get("descrizione") or "").strip(),
                "scollegato": False,
                "updated_by": request.user,
            },
        )

        if created:
            metadata.created_by = request.user
            metadata.save(update_fields=["created_by", "updated_at"])

        messages.success(request, "Descrizione file salvata.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaFileDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        relative_file = (request.POST.get("file") or "").strip()
        _, file_path = resolve_categoria_file_path(pratica_categoria, relative_file)

        file_path.unlink()
        metadata = PraticaCategoriaFile.objects.filter(
            pratica_categoria=pratica_categoria,
            percorso_relativo=relative_file,
            is_active=True,
        ).first()

        if metadata:
            metadata.soft_delete(user=request.user)

        messages.success(request, "File eliminato correttamente.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaFileUnlinkView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["pk"])
        relative_file = (request.POST.get("file") or "").strip()
        resolve_categoria_file_path(pratica_categoria, relative_file)

        metadata, created = PraticaCategoriaFile.objects.update_or_create(
            pratica_categoria=pratica_categoria,
            percorso_relativo=relative_file,
            is_active=True,
            defaults={
                "scollegato": True,
                "updated_by": request.user,
            },
        )

        if created:
            metadata.created_by = request.user
            metadata.save(update_fields=["created_by", "updated_at"])

        messages.success(request, "File scollegato dalla pratica.")
        return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])


class PraticaCategoriaAllegatoUploadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["categoria_pk"])
        uploaded_files = request.FILES.getlist("file")
        description = (request.POST.get("descrizione") or "").strip()

        if not uploaded_files:
            messages.error(request, "Seleziona un file valido da collegare.")
            return redirect("pratiche:pratica_detail", pk=kwargs["pratica_pk"])

        for uploaded_file in uploaded_files:
            PraticaCategoriaAllegato.objects.create(
                pratica_categoria=pratica_categoria,
                file=uploaded_file,
                descrizione=description,
                created_by=request.user,
                updated_by=request.user,
            )

        messages.success(request, f"{len(uploaded_files)} file singoli collegati correttamente.")
        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{pratica_categoria.pk}"
        )


class PraticaCategoriaAllegatoPickView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pratica_categoria = get_pratica_categoria_or_404(kwargs["pratica_pk"], kwargs["categoria_pk"])

        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            messages.error(request, f"Selettore file non disponibile: {exc}")
            return redirect(
                reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
                + f"#category-detail-{pratica_categoria.pk}"
            )

        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected_path = filedialog.askopenfilename(
                title="Seleziona file da collegare",
                filetypes=[
                    ("File supportati", "*.doc *.docx *.xls *.xlsx *.xlsm *.pdf *.png *.jpg *.jpeg *.txt *.html *.htm"),
                    ("Tutti i file", "*.*"),
                ],
            )
            root.destroy()
        except Exception as exc:
            messages.error(request, f"Impossibile aprire il selettore file: {exc}")
            return redirect(
                reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
                + f"#category-detail-{pratica_categoria.pk}"
            )

        if selected_path:
            try:
                create_category_attachment_from_path(pratica_categoria, selected_path, request.user)
                messages.success(request, "File singolo collegato correttamente.")
            except ValueError as exc:
                messages.error(request, str(exc))

        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{pratica_categoria.pk}"
        )


class PraticaCategoriaAllegatoFileView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )

        if not allegato.file:
            raise Http404("File non disponibile")

        return FileResponse(allegato.file.open("rb"), as_attachment=False, filename=allegato.file_nome)


class PraticaCategoriaAllegatoOpenView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )
        return_url = get_safe_next_url(request) or (
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{kwargs['categoria_pk']}"
        )

        if not allegato.file:
            return redirect(return_url)

        file_path = Path(allegato.file.path)

        if file_path.suffix.lower() not in NATIVE_OPEN_EXTENSIONS:
            return redirect(return_url)

        try:
            open_with_default_application(file_path)
            messages.success(request, f"File aperto: {allegato.file_nome}")
        except OSError as exc:
            messages.error(request, f"Impossibile aprire il file con l'applicazione originale: {exc}")

        return redirect(return_url)


class PraticaCategoriaAllegatoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )
        allegato.soft_delete(user=request.user)
        messages.success(request, "File singolo scollegato correttamente.")
        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{kwargs['categoria_pk']}"
        )


class PraticaCategoriaAllegatoDestroyView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        allegato = get_pratica_categoria_allegato_or_404(
            kwargs["pratica_pk"], kwargs["categoria_pk"], kwargs["pk"]
        )

        if allegato.file:
            allegato.file.delete(save=False)

        allegato.soft_delete(user=request.user)
        messages.success(request, "File singolo eliminato correttamente.")
        return redirect(
            reverse("pratiche:pratica_detail", kwargs={"pk": kwargs["pratica_pk"]})
            + f"#category-detail-{kwargs['categoria_pk']}"
        )


class FolderPickerView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            return JsonResponse({"error": f"Selettore cartella non disponibile: {exc}"}, status=500)

        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected_path = filedialog.askdirectory(title="Seleziona cartella pratica")
            root.destroy()
        except Exception as exc:
            return JsonResponse({"error": f"Impossibile aprire il selettore cartella: {exc}"}, status=500)

        if not selected_path:
            return JsonResponse({"path": ""})

        return JsonResponse({"path": selected_path})


class FolderPreviewView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        folder_value = (request.GET.get("path") or "").strip()

        if not folder_value:
            return JsonResponse({"files": [], "error": ""})

        if is_external_link(folder_value):
            return JsonResponse({"files": [], "is_link": True, "error": ""})

        folder_path = Path(folder_value).expanduser()

        if not folder_path.exists():
            return JsonResponse({"files": [], "error": "Cartella non trovata"})

        if not folder_path.is_dir():
            return JsonResponse({"files": [], "error": "Il percorso non è una cartella"})

        return JsonResponse({"files": get_supported_file_entries(folder_path), "error": ""})


class FolderPreviewFileOpenView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        _, file_path = resolve_preview_folder_file_path(
            request.GET.get("path") or "",
            request.GET.get("file") or "",
        )

        if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS:
            try:
                open_with_default_application(file_path)
                return JsonResponse({"opened": True, "message": f"File aperto: {file_path.name}"})
            except OSError as exc:
                return JsonResponse(
                    {"opened": False, "error": f"Impossibile aprire il file con l'applicazione originale: {exc}"},
                    status=500,
                )

        return FileResponse(file_path.open("rb"), as_attachment=False, filename=file_path.name)


class FolderPreviewFileDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        _, file_path = resolve_preview_folder_file_path(
            request.POST.get("path") or "",
            request.POST.get("file") or "",
        )
        file_path.unlink()
        return JsonResponse({"deleted": True, "message": f"File eliminato: {file_path.name}"})


class StudioTecnicoListView(LoginRequiredMixin, ListView):
    model = StudioTecnico
    template_name = "pratiche/studio_tecnico_list.html"
    context_object_name = "studi_tecnici"
    paginate_by = 20

    def get_queryset(self):
        queryset = StudioTecnico.objects.filter(is_active=True).annotate(
            tecnici_attivi=Count(
                "tecnici",
                filter=Q(tecnici__is_active=True),
                distinct=True,
            )
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(email__icontains=q)
                | Q(telefono__icontains=q)
            )

        return queryset.order_by("denominazione")


class StudioTecnicoCreateView(LoginRequiredMixin, CreateView):
    model = StudioTecnico
    form_class = StudioTecnicoForm
    template_name = "pratiche/studio_tecnico_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Studio tecnico creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:studio_tecnico_list")


class StudioTecnicoUpdateView(LoginRequiredMixin, UpdateView):
    model = StudioTecnico
    form_class = StudioTecnicoForm
    template_name = "pratiche/studio_tecnico_form.html"

    def get_queryset(self):
        return StudioTecnico.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Studio tecnico aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:studio_tecnico_list")


class StudioTecnicoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        studio = get_object_or_404(StudioTecnico, pk=kwargs["pk"], is_active=True)
        studio.soft_delete(user=request.user)
        messages.success(request, "Studio tecnico eliminato correttamente.")
        return redirect("pratiche:studio_tecnico_list")


class IncaricoTecnicoListView(LoginRequiredMixin, ListView):
    model = IncaricoTecnico
    template_name = "pratiche/incarico_tecnico_list.html"
    context_object_name = "incarichi"
    paginate_by = 20

    def get_queryset(self):
        queryset = IncaricoTecnico.objects.filter(is_active=True).annotate(
            tecnici_attivi=Count(
                "tecnici",
                filter=Q(tecnici__is_active=True),
                distinct=True,
            )
        )
        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(descrizione__icontains=q)
            )

        return queryset.order_by("denominazione")


class IncaricoTecnicoCreateView(LoginRequiredMixin, CreateView):
    model = IncaricoTecnico
    form_class = IncaricoTecnicoForm
    template_name = "pratiche/incarico_tecnico_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Incarico creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:incarico_tecnico_list")


class IncaricoTecnicoUpdateView(LoginRequiredMixin, UpdateView):
    model = IncaricoTecnico
    form_class = IncaricoTecnicoForm
    template_name = "pratiche/incarico_tecnico_form.html"

    def get_queryset(self):
        return IncaricoTecnico.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Incarico aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("pratiche:incarico_tecnico_list")


class IncaricoTecnicoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        incarico = get_object_or_404(IncaricoTecnico, pk=kwargs["pk"], is_active=True)
        incarico.soft_delete(user=request.user)
        messages.success(request, "Incarico eliminato correttamente.")
        return redirect("pratiche:incarico_tecnico_list")


class TecnicoCreateView(LoginRequiredMixin, CreateView):
    model = Tecnico
    form_class = TecnicoForm
    template_name = "pratiche/tecnico_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.pratica = get_object_or_404(Pratica, pk=kwargs["pratica_pk"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.pratica = self.pratica
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Tecnico aggiunto correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pratica"] = self.pratica
        context["page_title"] = "Nuovo tecnico"
        return context

    def get_success_url(self):
        return reverse_lazy("pratiche:pratica_detail", kwargs={"pk": self.pratica.pk})


class TecnicoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tecnico
    form_class = TecnicoForm
    template_name = "pratiche/tecnico_form.html"

    def get_queryset(self):
        return Tecnico.objects.filter(pratica_id=self.kwargs["pratica_pk"], is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Tecnico aggiornato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pratica"] = self.object.pratica
        context["page_title"] = "Modifica tecnico"
        return context

    def get_success_url(self):
        return reverse_lazy("pratiche:pratica_detail", kwargs={"pk": self.object.pratica_id})


class TecnicoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        tecnico = get_object_or_404(
            Tecnico,
            pk=kwargs["pk"],
            pratica_id=kwargs["pratica_pk"],
            is_active=True,
        )
        pratica_pk = tecnico.pratica_id
        tecnico.soft_delete(user=request.user)
        messages.success(request, "Tecnico eliminato correttamente.")
        return redirect("pratiche:pratica_detail", pk=pratica_pk)
