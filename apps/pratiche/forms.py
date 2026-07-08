from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.models import (
    CategoriaPratica,
    ComunicazionePratica,
    IncaricoTecnico,
    MacroCategoriaPratica,
    Pratica,
    PraticaCategoriaAllegato,
    PraticaCategoria,
    PraticaCategoriaFile,
    StudioTecnico,
    Tecnico,
    TemplatePratica,
)


class PraticaForm(forms.ModelForm):
    class Meta:
        model = Pratica
        fields = [
            "titolo",
            "cliente",
            "tipologia",
            "stato",
            "priorita",
            "data_apertura",
            "data_scadenza",
            "responsabile",
            "descrizione",
            "note",
        ]
        widgets = {
            "titolo": forms.TextInput(attrs={"class": "form-control"}),
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "tipologia": forms.Select(attrs={"class": "form-select"}),
            "stato": forms.Select(attrs={"class": "form-select"}),
            "priorita": forms.Select(attrs={"class": "form-select"}),
            "data_apertura": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "data_scadenza": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "responsabile": forms.Select(attrs={"class": "form-select"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Anagrafica.objects.filter(is_active=True)
        self.fields["responsabile"].required = False
        self.fields["data_apertura"].input_formats = ["%Y-%m-%d"]
        self.fields["data_scadenza"].required = False
        self.fields["data_scadenza"].input_formats = ["%Y-%m-%d"]

        if not self.instance.pk and not self.initial.get("data_apertura"):
            self.initial["data_apertura"] = timezone.localdate()


class TecnicoForm(forms.ModelForm):
    class Meta:
        model = Tecnico
        fields = [
            "nome",
            "cognome",
            "studio_appartenenza",
            "incarico",
            "email",
            "telefono",
            "note",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "cognome": forms.TextInput(attrs={"class": "form-control"}),
            "studio_appartenenza": forms.Select(attrs={"class": "form-select"}),
            "incarico": forms.Select(attrs={"class": "form-select"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["studio_appartenenza"].queryset = StudioTecnico.objects.filter(is_active=True)
        self.fields["studio_appartenenza"].required = False
        self.fields["incarico"].queryset = IncaricoTecnico.objects.filter(is_active=True)
        self.fields["incarico"].required = False


class StudioTecnicoForm(forms.ModelForm):
    class Meta:
        model = StudioTecnico
        fields = [
            "denominazione",
            "email",
            "telefono",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class IncaricoTecnicoForm(forms.ModelForm):
    class Meta:
        model = IncaricoTecnico
        fields = [
            "denominazione",
            "descrizione",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class CategoriaPraticaForm(forms.ModelForm):
    class Meta:
        model = CategoriaPratica
        fields = [
            "denominazione",
            "descrizione",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class MacroCategoriaPraticaForm(forms.ModelForm):
    class Meta:
        model = MacroCategoriaPratica
        fields = [
            "denominazione",
            "descrizione",
            "categorie",
            "note",
        ]
        widgets = {
            "denominazione": forms.TextInput(attrs={"class": "form-control"}),
            "descrizione": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "categorie": forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categorie"].queryset = CategoriaPratica.objects.filter(is_active=True)
        self.fields["categorie"].required = False
        self.fields["categorie"].help_text = (
            "Seleziona le categorie da creare automaticamente quando colleghi la macro-categoria alla pratica."
        )


class PraticaMacroCategoriaApplyForm(forms.Form):
    macro_categoria = forms.ModelChoiceField(
        label="Macro-categoria",
        queryset=MacroCategoriaPratica.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["macro_categoria"].queryset = MacroCategoriaPratica.objects.filter(is_active=True)


class TemplatePraticaForm(forms.ModelForm):
    class Meta:
        model = TemplatePratica
        fields = [
            "tipologia",
            "macro_categorie",
            "categorie",
            "note",
        ]
        widgets = {
            "tipologia": forms.Select(attrs={"class": "form-select"}),
            "macro_categorie": forms.SelectMultiple(attrs={"class": "form-select", "size": 7}),
            "categorie": forms.SelectMultiple(attrs={"class": "form-select", "size": 7}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["macro_categorie"].queryset = MacroCategoriaPratica.objects.filter(is_active=True)
        self.fields["macro_categorie"].required = False
        self.fields["categorie"].queryset = CategoriaPratica.objects.filter(is_active=True)
        self.fields["categorie"].required = False


class PraticaCategoriaForm(forms.ModelForm):
    class Meta:
        model = PraticaCategoria
        fields = [
            "macro_categoria",
            "categoria",
            "origine_template",
            "cartella",
            "versione",
            "note",
        ]
        widgets = {
            "macro_categoria": forms.Select(attrs={"class": "form-select"}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "origine_template": forms.HiddenInput(),
            "cartella": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": r"D:\Pratiche\Cliente\Cartella oppure https://...",
                }
            ),
            "versione": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.pratica = kwargs.pop("pratica", None)
        super().__init__(*args, **kwargs)
        self.fields["macro_categoria"].queryset = MacroCategoriaPratica.objects.filter(is_active=True)
        self.fields["macro_categoria"].required = False
        self.fields["categoria"].queryset = CategoriaPratica.objects.filter(is_active=True)
        self.fields["cartella"].help_text = (
            "Inserisci un percorso cartella accessibile dal server locale oppure un link web."
        )
        if self.instance.pk and self.instance.origine_template:
            self.fields["macro_categoria"].widget = forms.HiddenInput()
            self.fields["categoria"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        pratica = self.pratica or getattr(self.instance, "pratica", None)
        macro_categoria = cleaned_data.get("macro_categoria")
        categoria = cleaned_data.get("categoria")
        versione = (cleaned_data.get("versione") or "").strip()

        if not pratica or not categoria:
            return cleaned_data

        queryset = PraticaCategoria.objects.filter(
            pratica=pratica,
            macro_categoria=macro_categoria,
            categoria=categoria,
            versione=versione,
            is_active=True,
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            self.add_error(
                "versione",
                "Questa macro-categoria, categoria e versione sono gia' collegate alla pratica.",
            )

        cleaned_data["versione"] = versione
        return cleaned_data


class PraticaCategoriaFileUploadForm(forms.Form):
    file = forms.FileField(
        label="File",
        widget=forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"}),
    )
    descrizione = forms.CharField(
        label="Descrizione",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}),
    )


class PraticaCategoriaAllegatoUploadForm(forms.ModelForm):
    class Meta:
        model = PraticaCategoriaAllegato
        fields = ["file", "descrizione"]
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"}),
            "descrizione": forms.TextInput(
                attrs={"class": "form-control form-control-sm", "placeholder": "Descrizione del file"}
            ),
        }


class PraticaCategoriaFileDescriptionForm(forms.ModelForm):
    class Meta:
        model = PraticaCategoriaFile
        fields = ["descrizione"]
        widgets = {
            "descrizione": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
        }


class ComunicazionePraticaForm(forms.ModelForm):
    class Meta:
        model = ComunicazionePratica
        fields = ["data_ora", "descrizione", "allegato"]
        widgets = {
            "data_ora": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "descrizione": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descrivi la comunicazione, mittente/destinatario, oggetto o contenuto rilevante",
                }
            ),
            "allegato": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".eml,.msg,.pdf,.txt,.html,.htm,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg",
                }
            ),
        }


class BasePraticaCategoriaInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            macro_categoria = form.cleaned_data.get("macro_categoria")
            categoria = form.cleaned_data.get("categoria")
            versione = (form.cleaned_data.get("versione") or "").strip()

            if not categoria:
                continue

            key = (macro_categoria.pk if macro_categoria else None, categoria.pk, versione)

            if key in seen:
                raise forms.ValidationError(
                    "La stessa macro-categoria, categoria e versione e' presente piu' volte."
                )

            seen.add(key)


PraticaCategoriaFormSet = inlineformset_factory(
    Pratica,
    PraticaCategoria,
    form=PraticaCategoriaForm,
    formset=BasePraticaCategoriaInlineFormSet,
    fields=["macro_categoria", "categoria", "origine_template", "versione", "cartella", "note"],
    extra=1,
    can_delete=True,
)


TecnicoFormSet = inlineformset_factory(
    Pratica,
    Tecnico,
    form=TecnicoForm,
    fields=["nome", "cognome", "studio_appartenenza", "incarico", "email", "telefono", "note"],
    extra=1,
    can_delete=True,
)
