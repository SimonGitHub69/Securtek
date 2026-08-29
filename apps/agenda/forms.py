from django import forms

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda
from apps.agenda.services.notifiche import validate_smtp_security
from apps.pratiche.models import Pratica, Tecnico
from apps.pratiche.services.personale import tecnici_per_cliente


class EventoAgendaForm(forms.ModelForm):
    tecnici = forms.ModelMultipleChoiceField(
        label="Personale",
        queryset=Tecnico.objects.none(),
        required=False,
        widget=forms.MultipleHiddenInput(),
    )

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
            "giorni_preavviso",
            "descrizione",
            "note",
        ]
        widgets = {
            "pratica": forms.Select(attrs={"class": "form-select"}),
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "data_inizio": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "ora_inizio": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "data_fine": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "ora_fine": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "notifica_email": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "giorni_preavviso": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.cliente_id = kwargs.pop("cliente_id", None) or None
        super().__init__(*args, **kwargs)
        pratiche = (
            Pratica.objects.filter(is_active=True)
            .exclude(stato=Pratica.Stato.ARCHIVIATA)
            .select_related("cliente")
            .order_by("-data_apertura", "-id")
        )
        if self.cliente_id:
            pratiche = pratiche.filter(cliente_id=self.cliente_id)
        self.fields["pratica"].queryset = pratiche
        self.fields["data_inizio"].input_formats = ["%Y-%m-%d"]
        self.fields["data_fine"].required = False
        self.fields["data_fine"].input_formats = ["%Y-%m-%d"]
        self.fields["ora_inizio"].required = False
        self.fields["ora_fine"].required = False
        self.fields["giorni_preavviso"].help_text = (
            "Giorni prima della data evento/scadenza (data fine, oppure data inizio se assente) "
            "in cui inviare la notifica email. Con 0 l'invio avviene il giorno della scadenza."
        )

        if not self.instance.pk and self.fields["giorni_preavviso"].initial in (None, ""):
            self.fields["giorni_preavviso"].initial = ConfigurazioneNotificaEmail.get_solo().giorni_preavviso

        pratica_id = self.data.get("pratica") if self.is_bound else None
        if not pratica_id and self.instance.pk:
            pratica_id = self.instance.pratica_id
        if not pratica_id:
            pratica_id = self.initial.get("pratica")

        if pratica_id:
            pratica = (
                Pratica.objects.filter(pk=pratica_id)
                .only("id", "cliente_id")
                .first()
            )
            if pratica and pratica.cliente_id:
                self.fields["tecnici"].queryset = tecnici_per_cliente(
                    pratica.cliente_id,
                    pratica_id=pratica.pk,
                )
            else:
                self.fields["tecnici"].queryset = Tecnico.objects.filter(
                    pratica_id=pratica_id,
                    is_active=True,
                ).select_related("studio_appartenenza", "incarico", "pratica", "anagrafica")
        elif self.cliente_id:
            self.fields["tecnici"].queryset = tecnici_per_cliente(self.cliente_id)

        if self.instance.pk:
            self.fields["tecnici"].initial = self.instance.tecnici.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        data_inizio = cleaned_data.get("data_inizio")
        data_fine = cleaned_data.get("data_fine")
        pratica = cleaned_data.get("pratica")
        tecnici = cleaned_data.get("tecnici") or []

        if data_inizio and data_fine and data_fine < data_inizio:
            self.add_error("data_fine", "La data fine non puo' precedere la data inizio.")

        if pratica and tecnici:
            cliente_id = pratica.cliente_id
            invalid_tecnici = [
                tecnico
                for tecnico in tecnici
                if tecnico.anagrafica_id != cliente_id
                and (
                    not tecnico.pratica_id
                    or getattr(tecnico.pratica, "cliente_id", None) != cliente_id
                )
            ]
            if invalid_tecnici:
                self.add_error(
                    "tecnici",
                    "Il personale selezionato deve appartenere al cliente della pratica scelta.",
                )

        return cleaned_data

    def save(self, commit=True):
        evento = super().save(commit=commit)

        if commit:
            evento.tecnici.set(self.cleaned_data.get("tecnici") or [])

        return evento


class ConfigurazioneNotificaEmailForm(forms.ModelForm):
    class Meta:
        model = ConfigurazioneNotificaEmail
        fields = [
            "attiva",
            "host",
            "porta",
            "usa_tls",
            "usa_ssl",
            "verifica_certificato_ssl",
            "username",
            "password",
            "mittente",
            "destinatari_default",
            "giorni_preavviso",
            "note",
        ]
        widgets = {
            "attiva": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "host": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "smtp.dominio.it",
                    "autocomplete": "off",
                }
            ),
            "porta": forms.NumberInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "usa_tls": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "usa_ssl": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "verifica_certificato_ssl": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "off",
                }
            ),
            "password": forms.PasswordInput(
                render_value=True,
                attrs={
                    "class": "form-control",
                    "autocomplete": "new-password",
                },
            ),
            "mittente": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "inputmode": "email",
                    "autocomplete": "off",
                }
            ),
            "destinatari_default": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Una email per riga oppure separate da virgola",
                    "autocomplete": "off",
                }
            ),
            "giorni_preavviso": forms.NumberInput(attrs={"class": "form-control", "autocomplete": "off"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["giorni_preavviso"].help_text = (
            "Valore predefinito per i nuovi eventi agenda. Ogni evento puo' avere un preavviso diverso."
        )
        self.fields["password"].help_text = (
            "Lascia vuoto per mantenere la password gia' salvata."
        )
        self.fields["verifica_certificato_ssl"].help_text = (
            "Disattiva solo se il certificato del server non corrisponde al nome host SMTP."
        )

    def clean_password(self):
        password = self.cleaned_data.get("password", "")
        if password:
            return password
        if self.instance and self.instance.pk and self.instance.password:
            return self.instance.password
        return password

    def clean(self):
        cleaned_data = super().clean()

        security_error = validate_smtp_security(
            cleaned_data.get("porta"),
            cleaned_data.get("usa_tls"),
            cleaned_data.get("usa_ssl"),
        )
        if security_error:
            self.add_error("usa_ssl", security_error)

        if cleaned_data.get("attiva"):
            required_fields = ["host", "porta", "mittente"]
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, "Campo obbligatorio se le notifiche sono attive.")

        return cleaned_data
