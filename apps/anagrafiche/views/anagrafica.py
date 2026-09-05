from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View
from django.db.models import Count, Prefetch, Q
from django.contrib.messages.views import SuccessMessageMixin

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.anagrafiche.forms import AnagraficaForm, ContattoFormSet, IndirizzoFormSet, PersonaleFormSet
from apps.pratiche.models import Pratica, PraticaCategoria, Tecnico


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


def with_next(url, next_url):
    if not next_url:
        return url
    from urllib.parse import urlencode

    return f"{url}?{urlencode({'next': next_url})}"


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = Anagrafica.objects.filter(is_active=True)
        context["anagrafica_counts"] = {
            "totale": base_qs.count(),
            "con_contatti": base_qs.filter(contatti__is_active=True).distinct().count(),
            "con_indirizzi": base_qs.filter(indirizzi__is_active=True).distinct().count(),
            "con_pratiche": base_qs.filter(pratiche__is_active=True).distinct().count(),
        }

        params = self.request.GET.copy()
        params.pop("page", None)
        context["filter_query"] = params.urlencode()
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["has_filters"] = bool(context["q"])
        return context


class AnagraficaDetailView(LoginRequiredMixin, DetailView):
    model = Anagrafica
    template_name = "anagrafiche/anagrafica_detail.html"
    context_object_name = "anagrafica"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contatti"] = self.object.contatti.filter(is_active=True)
        context["indirizzi"] = (
            self.object.indirizzi.filter(is_active=True)
            .select_related("provincia", "comune")
        )
        context["personale"] = (
            self.object.personale.filter(is_active=True)
            .select_related("studio_appartenenza", "incarico")
            .order_by("cognome", "nome")
        )
        context["pratiche_in_essere"] = (
            self.object.pratiche.filter(is_active=True)
            .exclude(
                stato__in=[
                    Pratica.Stato.COMPLETATA,
                    Pratica.Stato.ANNULLATA,
                    Pratica.Stato.ARCHIVIATA,
                ]
            )
            .select_related("responsabile", "tipologia")
            .prefetch_related(
                Prefetch(
                    "categoria_collegamenti",
                    queryset=PraticaCategoria.objects.filter(is_active=True).select_related("categoria"),
                    to_attr="categorie_attive",
                )
            )
        )
        from apps.agenda.models import EventoAgenda

        context["eventi_agenda"] = list(
            EventoAgenda.objects.filter(
                is_active=True,
                pratica__cliente_id=self.object.pk,
                pratica__is_active=True,
            )
            .select_related("pratica", "pratica__tipologia")
            .prefetch_related("tecnici")
            .order_by("-data_inizio", "-ora_inizio", "-id")[:12]
        )
        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        context["back_url"] = next_url or reverse("anagrafiche:anagrafica_list")
        context["back_label"] = "Torna alla pratica" if next_url else "Elenco"
        return context


class AnagraficaFormsetMixin:
    contatto_prefix = "contatti"
    indirizzo_prefix = "indirizzi"
    personale_prefix = "personale"

    def get_contatto_queryset(self):
        if self.object:
            return self.object.contatti.filter(is_active=True)

        return Contatto.objects.none()

    def get_indirizzo_queryset(self):
        if self.object:
            return self.object.indirizzi.filter(is_active=True).select_related("provincia", "comune")

        return Indirizzo.objects.none()

    def get_personale_queryset(self):
        if self.object:
            return self.object.personale.filter(is_active=True)

        return Tecnico.objects.none()

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

    def get_personale_formset(self):
        return PersonaleFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix=self.personale_prefix,
            queryset=self.get_personale_queryset(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "contatto_formset" not in context:
            context["contatto_formset"] = self.get_contatto_formset()

        if "indirizzo_formset" not in context:
            context["indirizzo_formset"] = self.get_indirizzo_formset()

        if "personale_formset" not in context:
            context["personale_formset"] = self.get_personale_formset()

        next_url = get_safe_next_url(self.request)
        context["next_url"] = next_url
        if self.object:
            detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})
            context["cancel_url"] = with_next(detail_url, next_url)
        else:
            context["cancel_url"] = next_url or reverse("anagrafiche:anagrafica_list")
        return context

    def form_valid(self, form):
        contatto_formset = self.get_contatto_formset()
        indirizzo_formset = self.get_indirizzo_formset()
        personale_formset = self.get_personale_formset()

        if (
            not contatto_formset.is_valid()
            or not indirizzo_formset.is_valid()
            or not personale_formset.is_valid()
        ):
            return self.form_invalid_with_formsets(
                form,
                contatto_formset,
                indirizzo_formset,
                personale_formset,
            )

        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.updated_by = self.request.user
            if not self.object.pk:
                self.object.created_by = self.request.user
            self.object.save()

            self.save_formset(contatto_formset)
            self.save_formset(indirizzo_formset)
            self.save_personale_formset(personale_formset)

        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())

    def form_invalid_with_formsets(
        self,
        form,
        contatto_formset,
        indirizzo_formset,
        personale_formset,
    ):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                contatto_formset=contatto_formset,
                indirizzo_formset=indirizzo_formset,
                personale_formset=personale_formset,
            )
        )

    def save_formset(self, formset):
        formset.instance = self.object
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            if hasattr(obj, "soft_delete"):
                obj.soft_delete(user=self.request.user)
            else:
                obj.delete()

        for instance in instances:
            if hasattr(instance, "valore") and not instance.valore:
                continue

            if hasattr(instance, "indirizzo") and not instance.indirizzo:
                continue

            instance.updated_by = self.request.user
            if not instance.pk:
                instance.created_by = self.request.user
            instance.save()

    def save_personale_formset(self, formset):
        formset.instance = self.object
        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            if hasattr(obj, "soft_delete"):
                obj.soft_delete(user=self.request.user)
            else:
                obj.delete()

        for instance in instances:
            if not (instance.nome or "").strip() and not (instance.cognome or "").strip():
                continue

            instance.anagrafica = self.object
            instance.pratica = None
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
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})
        return with_next(detail_url, get_safe_next_url(self.request))


class AnagraficaUpdateView(LoginRequiredMixin, AnagraficaFormsetMixin, SuccessMessageMixin, UpdateView):
    model = Anagrafica
    form_class = AnagraficaForm
    template_name = "anagrafiche/anagrafica_form.html"
    success_message = "Anagrafica aggiornata correttamente."

    def get_success_url(self):
        detail_url = reverse("anagrafiche:anagrafica_detail", kwargs={"pk": self.object.pk})
        return with_next(detail_url, get_safe_next_url(self.request))


class AnagraficaDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        anagrafica = get_object_or_404(Anagrafica, pk=kwargs["pk"], is_active=True)
        anagrafica.soft_delete(user=request.user)
        messages.success(request, "Anagrafica eliminata correttamente.")
        return redirect("anagrafiche:anagrafica_list")
