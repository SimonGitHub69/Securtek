from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.db.models import Count, Prefetch, Q
from django.contrib.messages.views import SuccessMessageMixin

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.anagrafiche.forms import AnagraficaForm, ContattoFormSet, IndirizzoFormSet
from apps.pratiche.models import Pratica, PraticaCategoria


class AnagraficaListView(LoginRequiredMixin, ListView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_list.html"
    context_object_name = "anagrafiche"
    paginate_by = 20

    def get_queryset(self):
        queryset = Anagrafica.objects.filter(is_active=True).annotate(
            contatti_attivi=Count(
                "contatti",
                filter=Q(contatti__is_active=True),
                distinct=True,
            ),
            indirizzi_attivi=Count(
                "indirizzi",
                filter=Q(indirizzi__is_active=True),
                distinct=True,
            ),
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
        context["pratiche_in_essere"] = (
            self.object.pratiche.filter(is_active=True)
            .exclude(
                stato__in=[
                    Pratica.Stato.COMPLETATA,
                    Pratica.Stato.ANNULLATA,
                    Pratica.Stato.ARCHIVIATA,
                ]
            )
            .select_related("responsabile")
            .prefetch_related(
                Prefetch(
                    "categoria_collegamenti",
                    queryset=PraticaCategoria.objects.filter(is_active=True).select_related("categoria"),
                    to_attr="categorie_attive",
                )
            )
        )
        return context


class AnagraficaFormsetMixin:
    contatto_prefix = "contatti"
    indirizzo_prefix = "indirizzi"

    def get_contatto_queryset(self):
        if self.object:
            return self.object.contatti.filter(is_active=True)

        return Contatto.objects.none()

    def get_indirizzo_queryset(self):
        if self.object:
            return self.object.indirizzi.filter(is_active=True)

        return Indirizzo.objects.none()

    def get_contatto_formset(self):
        return ContattoFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix=self.contatto_prefix,
            queryset=self.get_contatto_queryset(),
        )

    def get_indirizzo_formset(self):
        return IndirizzoFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix=self.indirizzo_prefix,
            queryset=self.get_indirizzo_queryset(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "contatto_formset" not in context:
            context["contatto_formset"] = self.get_contatto_formset()

        if "indirizzo_formset" not in context:
            context["indirizzo_formset"] = self.get_indirizzo_formset()

        return context

    def form_valid(self, form):
        contatto_formset = self.get_contatto_formset()
        indirizzo_formset = self.get_indirizzo_formset()

        if not contatto_formset.is_valid() or not indirizzo_formset.is_valid():
            return self.form_invalid_with_formsets(form, contatto_formset, indirizzo_formset)

        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.updated_by = self.request.user
            if not self.object.pk:
                self.object.created_by = self.request.user
            self.object.save()

            self.save_formset(contatto_formset)
            self.save_formset(indirizzo_formset)

        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid_with_formsets(self, form, contatto_formset, indirizzo_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                contatto_formset=contatto_formset,
                indirizzo_formset=indirizzo_formset,
            )
        )

    def save_formset(self, formset):
        formset.instance = self.object
        instances = formset.save(commit=False)

        for instance in instances:
            if hasattr(instance, "valore") and not instance.valore:
                continue

            if hasattr(instance, "indirizzo") and not instance.indirizzo:
                continue

            instance.updated_by = self.request.user
            if not instance.pk:
                instance.created_by = self.request.user
            instance.save()


class AnagraficaCreateView(LoginRequiredMixin, AnagraficaFormsetMixin, SuccessMessageMixin, CreateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_message = "Anagrafica creata correttamente."

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})


class AnagraficaUpdateView(LoginRequiredMixin, AnagraficaFormsetMixin, SuccessMessageMixin, UpdateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_message = "Anagrafica aggiornata correttamente."

    def get_success_url(self):
        return reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})


class AnagraficaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        anagrafica = get_object_or_404(Anagrafica, pk=kwargs["pk"], is_active=True)
        anagrafica.soft_delete(user=request.user)
        messages.success(request, "Anagrafica eliminata correttamente.")
        return redirect("anagrafiche:anagrafica_list")
