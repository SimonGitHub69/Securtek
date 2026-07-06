from django import forms


class BaseForm(forms.Form):
    """
    Form base del progetto SECURTEK.

    Applica automaticamente lo stile Tabler/Bootstrap
    a tutti i campi.
    """

    default_class = "form-control"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} {self.default_class}".strip()

            if field.required:
                field.widget.attrs["required"] = "required"

            if not field.widget.attrs.get("placeholder"):
                field.widget.attrs["placeholder"] = field.label or name.replace("_", " ").title()

            field.widget.attrs.setdefault("autocomplete", "off")