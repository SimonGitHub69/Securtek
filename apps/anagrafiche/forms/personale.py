from django.forms import inlineformset_factory

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.forms import TecnicoForm
from apps.pratiche.models import Tecnico


PersonaleFormSet = inlineformset_factory(
    Anagrafica,
    Tecnico,
    form=TecnicoForm,
    fk_name="anagrafica",
    extra=1,
    can_delete=False,
)
