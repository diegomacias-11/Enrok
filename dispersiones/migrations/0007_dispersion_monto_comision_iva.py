from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispersiones", "0006_dispersion_ejecutivos"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispersion",
            name="monto_comision_iva",
            field=models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=12, null=True),
        ),
    ]
