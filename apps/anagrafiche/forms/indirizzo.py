from django import forms

from apps.anagrafiche.models import Indirizzo


class IndirizzoForm(forms.ModelForm):
    class Meta:
        model = Indirizzo
        fields = [
            "tipo",
            "indirizzo",
            "civico",
            "cap",
            "comune",
            "provincia",
            "nazione",
            "principale",
            "note",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "indirizzo": forms.TextInput(attrs={"class": "form-control"}),
            "civico": forms.TextInput(attrs={"class": "form-control"}),
            "cap": forms.TextInput(attrs={"class": "form-control"}),
            "comune": forms.TextInput(attrs={"class": "form-control"}),
            "provincia": forms.TextInput(attrs={"class": "form-control"}),
            "nazione": forms.TextInput(attrs={"class": "form-control"}),
            "principale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
