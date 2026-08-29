from django import forms

from apps.anagrafiche.models import Comune, Provincia


class ProvinciaForm(forms.ModelForm):
    class Meta:
        model = Provincia
        fields = [
            "sigla",
            "denominazione",
            "codice",
            "regione",
            "note",
        ]
        widgets = {
            "sigla": forms.TextInput(
                attrs={
                    "class": "form-control text-uppercase",
                    "maxlength": "2",
                    "autocomplete": "off",
                }
            ),
            "denominazione": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "codice": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "regione": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ComuneForm(forms.ModelForm):
    class Meta:
        model = Comune
        fields = [
            "denominazione",
            "provincia",
            "codice_istat",
            "codice_catastale",
            "cap",
            "popolazione",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "provincia": forms.Select(attrs={"class": "form-select"}),
            "codice_istat": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "codice_catastale": forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "cap": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "popolazione": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["provincia"].queryset = Provincia.objects.filter(is_active=True).order_by(
            "denominazione"
        )
