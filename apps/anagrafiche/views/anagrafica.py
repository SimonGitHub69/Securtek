from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.db.models import Count, Q
from django.contrib.messages.views import SuccessMessageMixin

from apps.anagrafiche.models import Anagrafica
from apps.anagrafiche.forms import AnagraficaForm


class AnagraficaListView(LoginRequiredMixin, ListView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_list.html"
    context_object_name = "anagrafiche"
    paginate_by = 20

    def get_queryset(self):
        queryset = Anagrafica.objects.filter(is_active=True).annotate(
            contatti_attivi=Count("contatti", filter=Q(contatti__is_active=True)),
            indirizzi_attivi=Count("indirizzi", filter=Q(indirizzi__is_active=True)),
        )

        q = (self.request.GET.get("q") or "").strip()

        if q:
            queryset = queryset.filter(
                Q(ragione_sociale__icontains=q) |
                Q(partita_iva__icontains=q) |
                Q(codice_fiscale__icontains=q) |
                Q(email__icontains=q) |
                Q(telefono__icontains=q)
            )

        return queryset.order_by("ragione_sociale")


class AnagraficaDetailView(LoginRequiredMixin, DetailView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_detail.html"
    context_object_name = "anagrafica"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contatti"] = self.object.contatti.filter(is_active=True)
        context["indirizzi"] = self.object.indirizzi.filter(is_active=True)
        return context


class AnagraficaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_url = reverse_lazy("anagrafiche:anagrafica_list")
    success_message = "Anagrafica creata correttamente."


class AnagraficaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_url = reverse_lazy("anagrafiche:anagrafica_list")
    success_message = "Anagrafica aggiornata correttamente."


class AnagraficaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        anagrafica = get_object_or_404(Anagrafica, pk=kwargs["pk"], is_active=True)
        anagrafica.soft_delete(user=request.user)
        messages.success(request, "Anagrafica eliminata correttamente.")
        return redirect("anagrafiche:anagrafica_list")
