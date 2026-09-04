from urllib.parse import parse_qsl, urlsplit

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, View

from apps.anagrafiche.models import Anagrafica
from apps.anagrafiche.views.anagrafica import get_safe_next_url
from apps.pratiche.forms import TecnicoForm
from apps.pratiche.models import Tecnico


def _return_to_pratica_personale(request, fallback_url: str) -> str:
    """Torna a next; se è una pratica, riapri sulla sezione Personale."""
    from apps.pratiche.views import parse_scroll_y, with_personale_position, with_scroll

    next_url = get_safe_next_url(request)
    if not next_url:
        return fallback_url

    url = next_url.split("#")[0]
    path = urlsplit(url).path or ""
    if "/pratiche/" in path and "/modifica" in path:
        existing = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
        scroll_y = parse_scroll_y(existing.get("scroll"))
        if scroll_y is None:
            scroll_y = parse_scroll_y(request.POST.get("scroll_y"))
        url = with_personale_position(url)
        return with_scroll(url, scroll_y)
    return url


class PersonaleAnagraficaCreateView(LoginRequiredMixin, CreateView):
    model = Tecnico
    form_class = TecnicoForm
    template_name = "anagrafiche/personale_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.anagrafica = get_object_or_404(Anagrafica, pk=kwargs["anagrafica_pk"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.anagrafica = self.anagrafica
        form.instance.pratica = None
        return form

    def form_valid(self, form):
        form.instance.anagrafica = self.anagrafica
        form.instance.pratica = None
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Personale aggiunto correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anagrafica"] = self.anagrafica
        context["page_title"] = "Nuovo personale"
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.anagrafica.pk})
        context["cancel_url"] = _return_to_pratica_personale(self.request, detail_url)
        return context

    def get_success_url(self):
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.anagrafica.pk})
        return _return_to_pratica_personale(self.request, detail_url)


class PersonaleAnagraficaUpdateView(LoginRequiredMixin, UpdateView):
    model = Tecnico
    form_class = TecnicoForm
    template_name = "anagrafiche/personale_form.html"

    def get_queryset(self):
        return Tecnico.objects.filter(
            anagrafica_id=self.kwargs["anagrafica_pk"],
            is_active=True,
        )

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Personale aggiornato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anagrafica"] = self.object.anagrafica
        context["page_title"] = "Modifica personale"
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.anagrafica_id})
        context["cancel_url"] = _return_to_pratica_personale(self.request, detail_url)
        return context

    def get_success_url(self):
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.anagrafica_id})
        return _return_to_pratica_personale(self.request, detail_url)


class PersonaleAnagraficaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        tecnico = get_object_or_404(
            Tecnico,
            pk=kwargs["pk"],
            anagrafica_id=kwargs["anagrafica_pk"],
            is_active=True,
        )
        anagrafica_pk = tecnico.anagrafica_id
        tecnico.soft_delete(user=request.user)
        messages.success(request, "Personale eliminato correttamente.")
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": anagrafica_pk})
        return redirect(_return_to_pratica_personale(request, detail_url))
