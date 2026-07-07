from django import forms

from apps.anagrafiche.models import Contatto


class ContattoForm(forms.ModelForm):
    class Meta:
        model = Contatto
        fields = [
            "tipo",
            "valore",
            "descrizione",
            "principale",
            "note",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "valore": forms.TextInput(attrs={"class": "form-control"}),
            "descrizione": forms.TextInput(attrs={"class": "form-control"}),
            "principale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
