import calendar
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, TemplateView, UpdateView, View

from apps.agenda.forms import ConfigurazioneNotificaEmailForm, EventoAgendaForm
from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda
from apps.pratiche.models import Pratica


class PraticaScadenzaAgendaItem:
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
        self.titolo = f"Scadenza {pratica.codice}"
        self.data_inizio = pratica.data_scadenza
        self.data_termine = pratica.data_scadenza

    def get_tipo_display(self):
        return "Scadenza pratica"

    def get_stato_display(self):
        return "Programmato"


def get_pratica_deadline_items(start_date, end_date, pratica_id=""):
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

    return [PraticaScadenzaAgendaItem(pratica) for pratica in pratiche]


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
        queryset = (
            EventoAgenda.objects.filter(is_active=True)
            .filter(data_inizio__lte=month_end)
            .filter(Q(data_fine__isnull=True, data_inizio__gte=month_start) | Q(data_fine__gte=month_start))
            .select_related("pratica", "pratica__cliente")
        )
        pratica_id = self.request.GET.get("pratica") or ""

        if pratica_id:
            queryset = queryset.filter(pratica_id=pratica_id)

        return queryset.order_by("data_inizio", "ora_inizio", "titolo")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month_start = self.get_month_date()
        _, days_in_month = calendar.monthrange(month_start.year, month_start.month)
        month_end = date(month_start.year, month_start.month, days_in_month)
        previous_month = date(month_start.year - 1, 12, 1) if month_start.month == 1 else date(month_start.year, month_start.month - 1, 1)
        next_month = date(month_start.year + 1, 1, 1) if month_start.month == 12 else date(month_start.year, month_start.month + 1, 1)
        pratica_id = self.request.GET.get("pratica") or ""
        events = list(self.get_events_queryset(month_start, month_end))
        events.extend(get_pratica_deadline_items(month_start, month_end, pratica_id))
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
                "selected_pratica": pratica_id,
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
        pratica_id = self.request.GET.get("pratica") or ""
        events = list(
            EventoAgenda.objects.filter(is_active=True)
            .filter(data_inizio__lte=selected_date)
            .filter(Q(data_fine__isnull=True, data_inizio=selected_date) | Q(data_fine__gte=selected_date))
            .select_related("pratica", "pratica__cliente")
            .order_by("ora_inizio", "tipo", "titolo")
        )

        if pratica_id:
            events = [event for event in events if str(event.pratica_id) == str(pratica_id)]

        events.extend(get_pratica_deadline_items(selected_date, selected_date, pratica_id))
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
                "selected_pratica": pratica_id,
            }
        )
        return context


class EventoAgendaCreateView(LoginRequiredMixin, CreateView):
    model = EventoAgenda
    form_class = EventoAgendaForm
    template_name = "agenda/evento_form.html"

    def get_initial(self):
        initial = super().get_initial()
        pratica_id = self.request.GET.get("pratica") or ""
        data = self.request.GET.get("data") or ""

        if pratica_id:
            initial["pratica"] = pratica_id

        if data:
            initial["data_inizio"] = data

        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Evento agenda creato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nuovo evento"
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        pratica_id = self.request.GET.get("pratica") or self.request.POST.get("pratica") or ""
        url = reverse("agenda:calendar")

        if pratica_id:
            return f"{url}?pratica={pratica_id}"

        return url


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
        return context

    def get_success_url(self):
        return f"{reverse('agenda:calendar')}?pratica={self.object.pratica_id}"


class EventoAgendaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        evento = get_object_or_404(EventoAgenda, pk=kwargs["pk"], is_active=True)
        pratica_id = evento.pratica_id
        evento.soft_delete(user=request.user)
        messages.success(request, "Evento agenda eliminato correttamente.")
        return redirect(f"{reverse('agenda:calendar')}?pratica={pratica_id}")


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

    def get_success_url(self):
        return reverse("agenda:configurazione_email")
