from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispersiones", "0009_dispersion_factura_solicitada"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispersion",
            name="forma_pago",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
