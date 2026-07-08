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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["indirizzo"].required = False

    def clean(self):
        cleaned_data = super().clean()
        has_details = any(
            cleaned_data.get(field_name)
            for field_name in [
                "indirizzo",
                "civico",
                "cap",
                "comune",
                "provincia",
                "principale",
                "note",
            ]
        )

        if has_details and not cleaned_data.get("indirizzo"):
            self.add_error("indirizzo", "Inserisci l'indirizzo.")

        return cleaned_data
