import calendar
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, ListView, TemplateView, UpdateView, View

from apps.anagrafiche.models import Anagrafica
from apps.agenda.forms import ConfigurazioneNotificaEmailForm, EventoAgendaForm
from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda, LogNotificaEmail
from apps.agenda.services.notifiche import send_test_email
from apps.pratiche.models import Pratica, Tecnico, TipologiaPratica


def get_safe_next_url(request):
    next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()
    if not next_url:
        return ""
    if not next_url.startswith("/") or next_url.startswith("//"):
        return ""
    if not url_has_allowed_host_and_scheme(
        next_url.split("#")[0] or next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ""
    return next_url


def evento_return_url(request, pratica_id=None):
    """Torna a next se presente (con scroll), altrimenti al dettaglio pratica."""
    from urllib.parse import urlsplit, urlunsplit

    next_url = get_safe_next_url(request)
    if next_url:
        # Rimuovi hash (#agenda): provoca salto; lo scroll resta nei query params.
        parts = urlsplit(next_url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))

    if pratica_id:
        return reverse("pratiche:pratica_detail", kwargs={"pk": pratica_id})
    return reverse("agenda:calendar")


class PraticaScadenzaAgendaItem:
    """Voce virtuale in calendario: la scadenza pratica non genera email.

    Le notifiche email riguardano solo EventoAgenda con notifica_email attiva.
    Per avvisare una scadenza pratica serve creare un evento agenda collegato.
    """
    tipo = EventoAgenda.Tipo.SCADENZA
    stato = EventoAgenda.Stato.PROGRAMMATO
    ora_inizio = None
    ora_fine = None
    data_fine = None
    descrizione = "Data scadenza indicata nella pratica."
    is_pratica_scadenza = True

    def __init__(self, pratica):
        self.pk = None
        self.pratica = pratica
        self.pratica_id = pratica.pk
        self.titolo = f"Scadenza {pratica.codice}"
        self.data_inizio = pratica.data_scadenza
        self.data_termine = pratica.data_scadenza

    def get_tipo_display(self):
        return "Scadenza pratica"

    def get_stato_display(self):
        return "Programmato"


def get_agenda_filters(request):
    return {
        "pratica_id": request.GET.get("pratica") or "",
        "tipologia_id": request.GET.get("tipologia") or "",
        "cliente_id": request.GET.get("cliente") or "",
    }


def build_agenda_query_prefix(pratica_id="", tipologia_id="", cliente_id=""):
    params = []
    if pratica_id:
        params.append(f"pratica={pratica_id}")
    if tipologia_id:
        params.append(f"tipologia={tipologia_id}")
    if cliente_id:
        params.append(f"cliente={cliente_id}")
    return f"?{'&'.join(params)}" if params else ""


def build_agenda_query_suffix(pratica_id="", tipologia_id="", cliente_id=""):
    prefix = build_agenda_query_prefix(pratica_id, tipologia_id, cliente_id)
    return prefix.replace("?", "&", 1) if prefix else ""


def get_selected_cliente(cliente_id):
    if not cliente_id:
        return None
    return Anagrafica.objects.filter(pk=cliente_id, is_active=True).first()


def get_agenda_filter_context(filters):
    return {
        "tipologie": TipologiaPratica.objects.filter(is_active=True).order_by("denominazione"),
        "clienti": Anagrafica.objects.filter(is_active=True).order_by("ragione_sociale"),
        "selected_pratica": filters["pratica_id"],
        "selected_tipologia": filters["tipologia_id"],
        "selected_cliente": filters["cliente_id"],
        "selected_pratica_obj": get_selected_pratica(filters["pratica_id"]),
        "selected_cliente_obj": get_selected_cliente(filters["cliente_id"]),
        "agenda_query_prefix": build_agenda_query_prefix(
            filters["pratica_id"],
            filters["tipologia_id"],
            filters["cliente_id"],
        ),
        "agenda_query_suffix": build_agenda_query_suffix(
            filters["pratica_id"],
            filters["tipologia_id"],
            filters["cliente_id"],
        ),
    }


def get_pratica_deadline_items(start_date, end_date, pratica_id="", tipologia_id="", cliente_id=""):
    stati_finali = [
        Pratica.Stato.COMPLETATA,
        Pratica.Stato.ANNULLATA,
        Pratica.Stato.ARCHIVIATA,
    ]
    pratiche = (
        Pratica.objects.filter(
            is_active=True,
            data_scadenza__gte=start_date,
            data_scadenza__lte=end_date,
        )
        .exclude(stato__in=stati_finali)
        .select_related("cliente")
        .order_by("data_scadenza", "codice")
    )

    if pratica_id:
        pratiche = pratiche.filter(pk=pratica_id)

    if tipologia_id:
        pratiche = pratiche.filter(tipologia_id=tipologia_id)

    if cliente_id:
        pratiche = pratiche.filter(cliente_id=cliente_id)

    return [PraticaScadenzaAgendaItem(pratica) for pratica in pratiche]


def get_selected_pratica(pratica_id):
    if not pratica_id:
        return None

    return Pratica.objects.filter(pk=pratica_id, is_active=True).first()


class AgendaCalendarView(LoginRequiredMixin, TemplateView):
    template_name = "agenda/agenda_calendar.html"

    def get_month_date(self):
        today = timezone.localdate()
        year = self.request.GET.get("year")
        month = self.request.GET.get("month")

        try:
            year = int(year or today.year)
            month = int(month or today.month)
            return date(year, month, 1)
        except ValueError:
            return date(today.year, today.month, 1)

    def get_events_queryset(self, month_start, month_end):
        filters = get_agenda_filters(self.request)
        queryset = (
            EventoAgenda.objects.filter(is_active=True)
            .filter(data_inizio__lte=month_end)
            .filter(Q(data_fine__isnull=True, data_inizio__gte=month_start) | Q(data_fine__gte=month_start))
            .select_related("pratica", "pratica__cliente", "pratica__tipologia")
            .prefetch_related("tecnici__studio_appartenenza", "tecnici__incarico")
        )

        if filters["pratica_id"]:
            queryset = queryset.filter(pratica_id=filters["pratica_id"])

        if filters["tipologia_id"]:
            queryset = queryset.filter(pratica__tipologia_id=filters["tipologia_id"])

        if filters["cliente_id"]:
            queryset = queryset.filter(pratica__cliente_id=filters["cliente_id"])

        return queryset.order_by("data_inizio", "ora_inizio", "titolo")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month_start = self.get_month_date()
        _, days_in_month = calendar.monthrange(month_start.year, month_start.month)
        month_end = date(month_start.year, month_start.month, days_in_month)
        previous_month = date(month_start.year - 1, 12, 1) if month_start.month == 1 else date(month_start.year, month_start.month - 1, 1)
        next_month = date(month_start.year + 1, 1, 1) if month_start.month == 12 else date(month_start.year, month_start.month + 1, 1)
        filters = get_agenda_filters(self.request)
        events = list(self.get_events_queryset(month_start, month_end))
        events.extend(
            get_pratica_deadline_items(
                month_start,
                month_end,
                filters["pratica_id"],
                filters["tipologia_id"],
                filters["cliente_id"],
            )
        )
        events.sort(key=lambda event: (event.data_inizio, event.ora_inizio or time.min, event.tipo, event.titolo))
        events_by_day = {}

        for event in events:
            current = max(event.data_inizio, month_start)
            end = min(event.data_termine, month_end)

            while current <= end:
                events_by_day.setdefault(current, []).append(event)
                current = date.fromordinal(current.toordinal() + 1)

        weeks = []
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month):
            weeks.append(
                [
                    {
                        "date": day,
                        "in_month": day.month == month_start.month,
                        "is_today": day == timezone.localdate(),
                        "events": events_by_day.get(day, []),
                    }
                    for day in week
                ]
            )

        today = timezone.localdate()
        context.update(
            {
                "month_start": month_start,
                "previous_month": previous_month,
                "next_month": next_month,
                "weeks": weeks,
                "events": events,
                "upcoming_events": [
                    event
                    for event in events
                    if event.data_termine >= today
                    and event.stato not in {EventoAgenda.Stato.COMPLETATO, EventoAgenda.Stato.ANNULLATO}
                ][:12],
                "pratiche": Pratica.objects.filter(is_active=True).order_by("-data_apertura", "-id"),
                **get_agenda_filter_context(filters),
            }
        )
        return context


class AgendaDayView(LoginRequiredMixin, TemplateView):
    template_name = "agenda/agenda_day.html"

    def get_selected_date(self):
        selected_date = self.request.GET.get("data") or ""

        try:
            return date.fromisoformat(selected_date)
        except ValueError:
            return timezone.localdate()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_date = self.get_selected_date()
        filters = get_agenda_filters(self.request)
        events = list(
            EventoAgenda.objects.filter(is_active=True)
            .filter(data_inizio__lte=selected_date)
            .filter(Q(data_fine__isnull=True, data_inizio=selected_date) | Q(data_fine__gte=selected_date))
            .select_related("pratica", "pratica__cliente", "pratica__tipologia")
            .prefetch_related("tecnici__studio_appartenenza", "tecnici__incarico")
            .order_by("ora_inizio", "tipo", "titolo")
        )

        if filters["pratica_id"]:
            events = [event for event in events if str(event.pratica_id) == str(filters["pratica_id"])]

        if filters["tipologia_id"]:
            events = [
                event
                for event in events
                if str(event.pratica.tipologia_id) == str(filters["tipologia_id"])
            ]

        if filters["cliente_id"]:
            events = [
                event
                for event in events
                if str(event.pratica.cliente_id) == str(filters["cliente_id"])
            ]

        events.extend(
            get_pratica_deadline_items(
                selected_date,
                selected_date,
                filters["pratica_id"],
                filters["tipologia_id"],
                filters["cliente_id"],
            )
        )
        events.sort(key=lambda event: (event.ora_inizio or time.min, event.tipo, event.titolo))

        previous_day = selected_date - timedelta(days=1)
        next_day = selected_date + timedelta(days=1)
        context.update(
            {
                "selected_date": selected_date,
                "previous_day": previous_day,
                "next_day": next_day,
                "events": events,
                "pratiche": Pratica.objects.filter(is_active=True).order_by("-data_apertura", "-id"),
                **get_agenda_filter_context(filters),
            }
        )
        return context


class EventoAgendaTecniciView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        pratica_id = request.GET.get("pratica") or ""

        if not pratica_id:
            return JsonResponse({"tecnici": []})

        pratica = (
            Pratica.objects.filter(pk=pratica_id, is_active=True)
            .select_related("cliente")
            .first()
        )
        if not pratica:
            return JsonResponse({"tecnici": []})

        # Personale dell'anagrafica cliente (e delle sue pratiche), deduplicato.
        from apps.pratiche.services.personale import deduplica_tecnici, tecnici_per_cliente

        if pratica.cliente_id:
            tecnici = deduplica_tecnici(
                tecnici_per_cliente(pratica.cliente_id, pratica_id=pratica.pk),
                prefer_pratica_id=pratica.pk,
            )
        else:
            tecnici = list(
                Tecnico.objects.filter(pratica_id=pratica.pk, is_active=True)
                .select_related("studio_appartenenza", "incarico")
                .order_by("cognome", "nome")
            )

        return JsonResponse(
            {
                "tecnici": [
                    {
                        "id": tecnico.pk,
                        "nome": tecnico.nome,
                        "cognome": tecnico.cognome,
                        "studio": tecnico.studio_appartenenza.denominazione if tecnico.studio_appartenenza else "",
                        "incarico": tecnico.incarico.denominazione if tecnico.incarico else "",
                        "email": tecnico.email or "",
                        "telefono": tecnico.telefono or "",
                        "pratica_id": tecnico.pratica_id,
                    }
                    for tecnico in tecnici
                ]
            }
        )


class EventoAgendaCreateView(LoginRequiredMixin, CreateView):
    model = EventoAgenda
    form_class = EventoAgendaForm
    template_name = "agenda/evento_form.html"

    def get_cliente_id(self):
        return (self.request.GET.get("cliente") or self.request.POST.get("cliente") or "").strip()

    def get_initial(self):
        initial = super().get_initial()
        pratica_id = self.request.GET.get("pratica") or ""
        data = self.request.GET.get("data") or ""
        cliente_id = self.get_cliente_id()

        if pratica_id:
            initial["pratica"] = pratica_id
        elif cliente_id:
            pratiche = list(
                Pratica.objects.filter(is_active=True, cliente_id=cliente_id)
                .exclude(stato=Pratica.Stato.ARCHIVIATA)
                .order_by("-data_apertura", "-id")[:2]
            )
            if len(pratiche) == 1:
                initial["pratica"] = pratiche[0].pk

        if data:
            try:
                data_evento = date.fromisoformat(data)
            except ValueError:
                data_evento = timezone.localdate()
        else:
            data_evento = timezone.localdate()

        initial["data_inizio"] = data_evento
        initial["data_fine"] = data_evento

        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["cliente_id"] = self.get_cliente_id() or None
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Evento agenda creato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nuovo evento"
        context["cancel_url"] = self.get_success_url()
        context["selected_tecnici_ids"] = []
        context["cliente_id"] = self.get_cliente_id()
        context["next_url"] = get_safe_next_url(self.request)
        return context

    def get_success_url(self):
        pratica_id = (
            getattr(getattr(self, "object", None), "pratica_id", None)
            or self.request.GET.get("pratica")
            or self.request.POST.get("pratica")
            or ""
        )
        return evento_return_url(self.request, pratica_id or None)


class EventoAgendaUpdateView(LoginRequiredMixin, UpdateView):
    model = EventoAgenda
    form_class = EventoAgendaForm
    template_name = "agenda/evento_form.html"

    def get_queryset(self):
        return EventoAgenda.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Evento agenda aggiornato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Modifica evento"
        context["cancel_url"] = self.get_success_url()
        context["next_url"] = get_safe_next_url(self.request)
        context["selected_tecnici_ids"] = list(
            self.object.tecnici.filter(is_active=True).values_list("pk", flat=True)
        )
        return context

    def get_success_url(self):
        return evento_return_url(self.request, self.object.pratica_id)


class EventoAgendaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        evento = get_object_or_404(EventoAgenda, pk=kwargs["pk"], is_active=True)
        pratica_id = evento.pratica_id
        evento.soft_delete(user=request.user)
        messages.success(request, "Evento agenda eliminato correttamente.")
        return redirect(evento_return_url(request, pratica_id))


class ConfigurazioneNotificaEmailUpdateView(LoginRequiredMixin, UpdateView):
    model = ConfigurazioneNotificaEmail
    form_class = ConfigurazioneNotificaEmailForm
    template_name = "agenda/configurazione_email_form.html"

    def get_object(self, queryset=None):
        return ConfigurazioneNotificaEmail.get_solo()

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        if not form.instance.created_by:
            form.instance.created_by = self.request.user
        messages.success(self.request, "Parametri mail notifiche aggiornati correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.agenda.services.servizio_notifiche import get_servizio_status

        context["recent_logs"] = (
            LogNotificaEmail.objects.filter(is_active=True)
            .select_related("evento", "pratica")
            .order_by("-inviata_il", "-id")[:8]
        )
        context["log_count"] = LogNotificaEmail.objects.filter(is_active=True).count()
        context["servizio_status"] = get_servizio_status(self.object)
        return context

    def get_success_url(self):
        return reverse("agenda:configurazione_email")


class ConfigurazioneNotificaEmailServizioView(LoginRequiredMixin, View):
    """Accende o spegne il servizio automatico senza toccare SMTP."""

    def post(self, request, *args, **kwargs):
        config = ConfigurazioneNotificaEmail.get_solo()
        action = (request.POST.get("action") or "").strip().lower()
        if action == "off":
            config.servizio_attivo = False
            messages.success(request, "Servizio automatico mail spento.")
        elif action == "on":
            config.servizio_attivo = True
            messages.success(request, "Servizio automatico mail acceso.")
        else:
            messages.error(request, "Azione non valida.")
            return redirect("agenda:configurazione_email")
        config.updated_by = request.user
        config.save(update_fields=["servizio_attivo", "updated_by", "updated_at"])
        return redirect("agenda:configurazione_email")


class LogNotificaEmailClearView(LoginRequiredMixin, View):
    """Azzera il registro mail (soft-delete di tutte le voci attive)."""

    def post(self, request, *args, **kwargs):
        now = timezone.now()
        updated = LogNotificaEmail.objects.filter(is_active=True).update(
            is_active=False,
            deleted_at=now,
            deleted_by=request.user,
            updated_at=now,
        )
        if updated:
            messages.success(
                request,
                f"Registro mail azzerato ({updated} voc{'e' if updated == 1 else 'i'} rimosse).",
            )
        else:
            messages.info(request, "Il registro mail era già vuoto.")
        return redirect("agenda:configurazione_email")


class LogNotificaEmailListView(LoginRequiredMixin, ListView):
    model = LogNotificaEmail
    template_name = "agenda/log_notifiche_email_list.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        queryset = (
            LogNotificaEmail.objects.filter(is_active=True)
            .select_related("evento", "pratica", "pratica__cliente")
            .order_by("-inviata_il", "-id")
        )
        esito = (self.request.GET.get("esito") or "").strip()
        tipo = (self.request.GET.get("tipo") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        if esito:
            queryset = queryset.filter(esito=esito)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if q:
            queryset = queryset.filter(
                Q(oggetto__icontains=q)
                | Q(destinatari__icontains=q)
                | Q(pratica__codice__icontains=q)
                | Q(pratica__titolo__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config"] = ConfigurazioneNotificaEmail.get_solo()
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["esito"] = (self.request.GET.get("esito") or "").strip()
        context["tipo"] = (self.request.GET.get("tipo") or "").strip()
        context["esito_choices"] = LogNotificaEmail.Esito.choices
        context["tipo_choices"] = LogNotificaEmail.Tipo.choices
        params = self.request.GET.copy()
        params.pop("page", None)
        context["filter_query"] = params.urlencode()
        return context


class ConfigurazioneNotificaEmailTestView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        destinatario = (request.POST.get("destinatario") or "").strip()
        if not destinatario:
            messages.error(request, "Indica un indirizzo email di destinazione.")
            return redirect("agenda:configurazione_email")

        try:
            validate_email(destinatario)
        except ValidationError:
            messages.error(request, "L'indirizzo email di destinazione non e' valido.")
            return redirect("agenda:configurazione_email")

        result = send_test_email(recipients=[destinatario], user=request.user)
        if result["ok"]:
            messages.success(
                request,
                f"Email di test inviata correttamente a: {destinatario}.",
            )
        else:
            messages.error(request, f"Invio email di test fallito: {result['error']}")
        return redirect("agenda:configurazione_email")
