from django import forms

from apps.anagrafiche.models import Comune, Indirizzo, Provincia


class IndirizzoForm(forms.ModelForm):
    class Meta:
        model = Indirizzo
        fields = [
            "tipo",
            "indirizzo",
            "civico",
            "provincia",
            "comune",
            "cap",
            "nazione",
            "principale",
            "note",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "indirizzo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "civico": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "cap": forms.TextInput(
                attrs={
                    "class": "form-control js-cap-input",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "provincia": forms.Select(
                attrs={
                    "class": "form-select js-provincia-select",
                    "data-comuni-url": "/anagrafiche/api/comuni/",
                    "autocomplete": "off",
                }
            ),
            "comune": forms.Select(
                attrs={
                    "class": "form-select js-comune-select",
                    "autocomplete": "off",
                }
            ),
            "nazione": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "principale": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "autocomplete": "off",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["indirizzo"].required = False
        self.fields["provincia"].required = False
        self.fields["comune"].required = False
        self.fields["provincia"].queryset = Provincia.objects.filter(is_active=True).order_by(
            "denominazione"
        )
        self.fields["provincia"].empty_label = "---------"

        provincia_id = None
        if self.is_bound:
            raw = self.data.get(self.add_prefix("provincia"))
            if raw:
                try:
                    provincia_id = int(raw)
                except (TypeError, ValueError):
                    provincia_id = None
        elif self.instance and self.instance.provincia_id:
            provincia_id = self.instance.provincia_id
        elif self.initial.get("provincia"):
            provincia_id = self.initial.get("provincia")

        comuni = Comune.objects.filter(is_active=True).select_related("provincia")
        if provincia_id:
            comuni = comuni.filter(provincia_id=provincia_id)
        elif self.instance and self.instance.comune_id:
            comuni = comuni.filter(pk=self.instance.comune_id)
        else:
            comuni = comuni.none()

        self.fields["comune"].queryset = comuni.order_by("denominazione")
        self.fields["comune"].empty_label = "---------"

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

        provincia = cleaned_data.get("provincia")
        comune = cleaned_data.get("comune")
        if comune and provincia and comune.provincia_id != provincia.pk:
            self.add_error("comune", "Il comune non appartiene alla provincia selezionata.")
        elif comune and not provincia:
            cleaned_data["provincia"] = comune.provincia

        if comune and not cleaned_data.get("cap") and comune.cap:
            cleaned_data["cap"] = comune.cap

        return cleaned_data
