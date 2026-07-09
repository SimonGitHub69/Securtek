from django import forms
from django.forms import inlineformset_factory

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.anagrafiche.forms.contatto import ContattoForm
from apps.anagrafiche.forms.indirizzo import IndirizzoForm


class AnagraficaForm(forms.ModelForm):

    class Meta:
        model = Anagrafica
        fields = [
            "ragione_sociale",
            "partita_iva",
            "codice_fiscale",
            "email",
            "telefono",
        ]

        widgets = {
            "ragione_sociale": forms.TextInput(attrs={"class": "form-control"}),
            "partita_iva": forms.TextInput(attrs={"class": "form-control"}),
            "codice_fiscale": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
        }


ContattoFormSet = inlineformset_factory(
    Anagrafica,
    Contatto,
    form=ContattoForm,
    extra=1,
    can_delete=False,
)


IndirizzoFormSet = inlineformset_factory(
    Anagrafica,
    Indirizzo,
    form=IndirizzoForm,
    extra=1,
    can_delete=False,
)
