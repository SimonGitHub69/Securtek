from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, View

from apps.anagrafiche.forms import IndirizzoForm
from apps.anagrafiche.models import Anagrafica, Indirizzo


class IndirizzoCreateView(LoginRequiredMixin, CreateView):
    model = Indirizzo
    form_class = IndirizzoForm
    template_name = "anagrafiche/indirizzo_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.anagrafica = get_object_or_404(Anagrafica, pk=kwargs["anagrafica_pk"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.anagrafica = self.anagrafica
        messages.success(self.request, "Indirizzo aggiunto correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anagrafica"] = self.anagrafica
        context["page_title"] = "Nuovo indirizzo"
        return context

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.anagrafica.pk})


class IndirizzoUpdateView(LoginRequiredMixin, UpdateView):
    model = Indirizzo
    form_class = IndirizzoForm
    template_name = "anagrafiche/indirizzo_form.html"

    def get_queryset(self):
        return Indirizzo.objects.filter(
            anagrafica_id=self.kwargs["anagrafica_pk"],
            is_active=True,
        )

    def form_valid(self, form):
        messages.success(self.request, "Indirizzo aggiornato correttamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anagrafica"] = self.object.anagrafica
        context["page_title"] = "Modifica indirizzo"
        return context

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.anagrafica_id})


class IndirizzoDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        indirizzo = get_object_or_404(
            Indirizzo,
            pk=kwargs["pk"],
            anagrafica_id=kwargs["anagrafica_pk"],
            is_active=True,
        )
        anagrafica_pk = indirizzo.anagrafica_id
        indirizzo.soft_delete(user=request.user)
        messages.success(request, "Indirizzo eliminato correttamente.")
        return redirect("anagrafiche:anagrafica_detail", pk=anagrafica_pk)
