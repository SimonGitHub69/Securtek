from django import forms
from django.forms import inlineformset_factory

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.forms import TecnicoForm
from apps.pratiche.models import Tecnico


class PersonaleForm(TecnicoForm):
    """Form personale in anagrafica: note su una sola riga."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
            }
        )


PersonaleFormSet = inlineformset_factory(
    Anagrafica,
    Tecnico,
    form=PersonaleForm,
    fk_name="anagrafica",
    extra=1,
    can_delete=True,
)
