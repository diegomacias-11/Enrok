from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dispersiones", "0007_dispersion_monto_comision_iva"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dispersion",
            name="ejecutivo2",
        ),
        migrations.RemoveField(
            model_name="dispersion",
            name="ejecutivo_apoyo",
        ),
    ]
