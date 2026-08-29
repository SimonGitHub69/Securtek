# Generated manually for Indirizzo FK to Provincia/Comune

import django.db.models.deletion
from django.db import migrations, models


def migrate_indirizzi_territorio(apps, schema_editor):
    Indirizzo = apps.get_model("anagrafiche", "Indirizzo")
    Provincia = apps.get_model("anagrafiche", "Provincia")
    Comune = apps.get_model("anagrafiche", "Comune")

    province_by_sigla = {
        p.sigla.upper(): p
        for p in Provincia.objects.filter(is_active=True)
        if p.sigla
    }

    for indirizzo in Indirizzo.objects.all().iterator():
        provincia = None
        comune = None
        sigla = (indirizzo.provincia_sigla or "").strip().upper()
        nome = (indirizzo.comune_nome or "").strip()

        if sigla:
            provincia = province_by_sigla.get(sigla)

        if nome:
            comuni = Comune.objects.filter(is_active=True, denominazione__iexact=nome)
            if provincia:
                comuni = comuni.filter(provincia_id=provincia.pk)
            comune = comuni.first()
            if comune and not provincia:
                provincia = comune.provincia

        update_fields = []
        if provincia and indirizzo.provincia_id != provincia.pk:
            indirizzo.provincia = provincia
            update_fields.append("provincia")
        if comune and indirizzo.comune_id != comune.pk:
            indirizzo.comune = comune
            update_fields.append("comune")
        if update_fields:
            indirizzo.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("anagrafiche", "0005_provincia_comune"),
    ]

    operations = [
        migrations.RenameField(
            model_name="indirizzo",
            old_name="provincia",
            new_name="provincia_sigla",
        ),
        migrations.RenameField(
            model_name="indirizzo",
            old_name="comune",
            new_name="comune_nome",
        ),
        migrations.AddField(
            model_name="indirizzo",
            name="provincia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="indirizzi",
                to="anagrafiche.provincia",
                verbose_name="Provincia",
            ),
        ),
        migrations.AddField(
            model_name="indirizzo",
            name="comune",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="indirizzi",
                to="anagrafiche.comune",
                verbose_name="Comune",
            ),
        ),
        migrations.RunPython(migrate_indirizzi_territorio, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="indirizzo",
            name="provincia_sigla",
        ),
        migrations.RemoveField(
            model_name="indirizzo",
            name="comune_nome",
        ),
    ]
