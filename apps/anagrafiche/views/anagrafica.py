from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.db.models import Q

from apps.anagrafiche.models import Anagrafica
from apps.anagrafiche.forms import AnagraficaForm


class AnagraficaListView(LoginRequiredMixin, ListView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_list.html"
    context_object_name = "anagrafiche"
    paginate_by = 20

    def get_queryset(self):
        queryset = Anagrafica.objects.filter(is_active=True)

        q = self.request.GET.get("q")

        if q:
            queryset = queryset.filter(
                Q(ragione_sociale__icontains=q) |
                Q(partita_iva__icontains=q) |
                Q(codice_fiscale__icontains=q) |
                Q(email__icontains=q) |
                Q(telefono__icontains=q)
            )

        return queryset.order_by("ragione_sociale")


class AnagraficaCreateView(LoginRequiredMixin, CreateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_url = reverse_lazy("anagrafiche:anagrafica_list")


class AnagraficaUpdateView(LoginRequiredMixin, UpdateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_url = reverse_lazy("anagrafiche:anagrafica_list")