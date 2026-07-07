from django import forms

from apps.anagrafiche.models import Anagrafica


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