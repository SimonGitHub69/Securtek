from django import forms
from django.forms import inlineformset_factory

from apps.anagrafiche.models import Anagrafica, Contatto, Indirizzo
from apps.anagrafiche.forms.contatto import ContattoForm
from apps.anagrafiche.forms.indirizzo import IndirizzoForm
from apps.anagrafiche.forms.personale import PersonaleFormSet  # noqa: F401


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
            "ragione_sociale": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "partita_iva": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "codice_fiscale": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                    "spellcheck": "false",
                    "autocapitalize": "characters",
                }
            ),
            "email": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "email",
                    "autocomplete": "off",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "tel",
                    "autocomplete": "off",
                }
            ),
        }


ContattoFormSet = inlineformset_factory(
    Anagrafica,
    Contatto,
    form=ContattoForm,
    extra=1,
    can_delete=True,
)


IndirizzoFormSet = inlineformset_factory(
    Anagrafica,
    Indirizzo,
    form=IndirizzoForm,
    extra=1,
    can_delete=True,
)
