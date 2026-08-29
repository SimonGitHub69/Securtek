from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from apps.anagrafiche.forms.territorio import ComuneForm, ProvinciaForm
from apps.anagrafiche.models import Comune, Provincia


def _search_list_context(request):
    q = (request.GET.get("q") or "").strip()
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "q": q,
        "has_filters": bool(q) or bool((request.GET.get("provincia") or "").strip()),
        "filter_query": params.urlencode(),
    }


class ProvinciaListView(LoginRequiredMixin, ListView):
    model = Provincia
    template_name = "anagrafiche/provincia_list.html"
    context_object_name = "province"
    paginate_by = 30

    def get_queryset(self):
        queryset = Provincia.objects.filter(is_active=True).annotate(
            comuni_attivi=Count("comuni", filter=Q(comuni__is_active=True), distinct=True)
        )
        q = (self.request.GET.get("q") or "").strip()
        if q:
            queryset = queryset.filter(
                Q(sigla__icontains=q)
                | Q(denominazione__icontains=q)
                | Q(regione__icontains=q)
                | Q(codice__icontains=q)
            )
        return queryset.order_by("denominazione")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_search_list_context(self.request))
        base_qs = Provincia.objects.filter(is_active=True)
        context["provincia_counts"] = {
            "totale": base_qs.count(),
            "con_comuni": base_qs.filter(comuni__is_active=True).distinct().count(),
            "regioni": base_qs.exclude(regione="").values("regione").distinct().count(),
        }
        return context


class ProvinciaCreateView(LoginRequiredMixin, CreateView):
    model = Provincia
    form_class = ProvinciaForm
    template_name = "anagrafiche/provincia_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Provincia creata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("anagrafiche:provincia_list")


class ProvinciaUpdateView(LoginRequiredMixin, UpdateView):
    model = Provincia
    form_class = ProvinciaForm
    template_name = "anagrafiche/provincia_form.html"

    def get_queryset(self):
        return Provincia.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Provincia aggiornata correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("anagrafiche:provincia_list")


class ProvinciaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        provincia = get_object_or_404(Provincia, pk=kwargs["pk"], is_active=True)
        if provincia.comuni.filter(is_active=True).exists():
            messages.error(
                request,
                "Impossibile eliminare la provincia: ci sono ancora comuni collegati.",
            )
            return redirect("anagrafiche:provincia_list")
        provincia.soft_delete(user=request.user)
        messages.success(request, "Provincia eliminata correttamente.")
        return redirect("anagrafiche:provincia_list")


class ComuneListView(LoginRequiredMixin, ListView):
    model = Comune
    template_name = "anagrafiche/comune_list.html"
    context_object_name = "comuni"
    paginate_by = 30

    def get_queryset(self):
        queryset = Comune.objects.filter(is_active=True).select_related("provincia")
        q = (self.request.GET.get("q") or "").strip()
        provincia = (self.request.GET.get("provincia") or "").strip().upper()

        if q:
            queryset = queryset.filter(
                Q(denominazione__icontains=q)
                | Q(cap__icontains=q)
                | Q(codice_istat__icontains=q)
                | Q(codice_catastale__icontains=q)
                | Q(provincia__sigla__icontains=q)
                | Q(provincia__denominazione__icontains=q)
            )
        if provincia:
            queryset = queryset.filter(provincia__sigla=provincia)

        return queryset.order_by("denominazione", "provincia__sigla")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_search_list_context(self.request))
        context["provincia_filter"] = (self.request.GET.get("provincia") or "").strip().upper()
        context["province"] = Provincia.objects.filter(is_active=True).order_by("denominazione")
        base_qs = Comune.objects.filter(is_active=True)
        context["comune_counts"] = {
            "totale": base_qs.count(),
            "con_cap": base_qs.exclude(cap="").count(),
            "province": base_qs.values("provincia_id").distinct().count(),
        }
        return context


class ComuneCreateView(LoginRequiredMixin, CreateView):
    model = Comune
    form_class = ComuneForm
    template_name = "anagrafiche/comune_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Comune creato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("anagrafiche:comune_list")


class ComuneUpdateView(LoginRequiredMixin, UpdateView):
    model = Comune
    form_class = ComuneForm
    template_name = "anagrafiche/comune_form.html"

    def get_queryset(self):
        return Comune.objects.filter(is_active=True)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Comune aggiornato correttamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("anagrafiche:comune_list")


class ComuneDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        comune = get_object_or_404(Comune, pk=kwargs["pk"], is_active=True)
        comune.soft_delete(user=request.user)
        messages.success(request, "Comune eliminato correttamente.")
        return redirect("anagrafiche:comune_list")


class ComuneJsonView(LoginRequiredMixin, View):
    """Comuni filtrati per provincia (sigla), usati negli indirizzi."""

    def get(self, request, *args, **kwargs):
        sigla = (request.GET.get("provincia") or "").strip().upper()
        provincia_id = (request.GET.get("provincia_id") or "").strip()
        q = (request.GET.get("q") or "").strip()

        comuni = Comune.objects.filter(is_active=True).select_related("provincia")
        if provincia_id:
            comuni = comuni.filter(provincia_id=provincia_id)
        elif sigla:
            comuni = comuni.filter(provincia__sigla=sigla)
        if q:
            comuni = comuni.filter(denominazione__icontains=q)

        comuni = comuni.order_by("denominazione")[:500]
        return JsonResponse(
            {
                "comuni": [
                    {
                        "id": comune.pk,
                        "nome": comune.denominazione,
                        "cap": comune.cap or "",
                        "provincia": comune.provincia.sigla,
                        "provincia_id": comune.provincia_id,
                    }
                    for comune in comuni
                ]
            }
        )
