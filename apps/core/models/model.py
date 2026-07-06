from django.forms import ModelForm

from .base import BaseForm


class BaseModelForm(BaseForm, ModelForm):
    """
    Classe base per tutti i ModelForm.
    """

    pass