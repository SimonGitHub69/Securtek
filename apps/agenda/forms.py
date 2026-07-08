from django import forms

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda
from apps.pratiche.models import Pratica


class EventoAgendaForm(forms.ModelForm):
    class Meta:
        model = EventoAgenda
        fields = [
            "pratica",
            "titolo",
            "tipo",
            "stato",
            "data_inizio",
            "ora_inizio",
            "data_fine",
            "ora_fine",
            "notifica_email",
            "descrizione",
            "note",
        ]
        widgets = {
            "pratica": forms.Select(attrs={"class": "form-select"}),
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "data_inizio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ora_inizio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "data_fine": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ora_fine": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "notifica_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pratica"].queryset = (
            Pratica.objects.filter(is_active=True)
            .exclude(stato=Pratica.Stato.ARCHIVIATA)
            .select_related("cliente")
            .order_by("-data_apertura", "-id")
        )
        self.fields["data_fine"].required = False
        self.fields["ora_inizio"].required = False
        self.fields["ora_fine"].required = False

    def clean(self):
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get("data_inizio")
        data_fine = cleaned_data.get("data_fine")

        if data_inizio and data_fine and data_fine < data_inizio:
            self.add_error("data_fine", "La data fine non puo' precedere la data inizio.")

        return cleaned_data


class ConfigurazioneNotificaEmailForm(forms.ModelForm):
    class Meta:
        model = ConfigurazioneNotificaEmail
        fields = [
            "attiva",
            "host",
            "porta",
            "usa_tls",
            "usa_ssl",
            "username",
            "password",
            "mittente",
            "destinatari_default",
            "giorni_preavviso",
            "note",
        ]
        widgets = {
            "attiva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "host": forms.TextInput(attrs={"class": "form-control", "placeholder": "smtp.dominio.it"}),
            "porta": forms.NumberInput(attrs={"class": "form-control"}),
            "usa_tls": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "usa_ssl": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "password": forms.PasswordInput(attrs={"class": "form-control", "render_value": True}),
            "mittente": forms.EmailInput(attrs={"class": "form-control"}),
            "destinatari_default": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Una email per riga oppure separate da virgola",
                }
            ),
            "giorni_preavviso": forms.NumberInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("usa_tls") and cleaned_data.get("usa_ssl"):
            self.add_error("usa_ssl", "TLS e SSL non possono essere attivi insieme.")

        if cleaned_data.get("attiva"):
            required_fields = ["host", "porta", "mittente"]
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, "Campo obbligatorio se le notifiche sono attive.")

        return cleaned_data
