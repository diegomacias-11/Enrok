from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispersiones", "0008_remove_dispersion_ejecutivo2_ejecutivo_apoyo"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispersion",
            name="factura_solicitada",
            field=models.BooleanField(default=False),
        ),
    ]
