from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, View

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.forms import TecnicoForm
from apps.pratiche.models import Tecnico


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
        return context

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.anagrafica.pk})


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
        return context

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.anagrafica_id})


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
        return redirect("anagrafiche:anagrafica_detail", pk=anagrafica_pk)
