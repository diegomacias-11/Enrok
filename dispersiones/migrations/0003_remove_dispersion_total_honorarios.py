from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dispersiones", "0002_rename_factura_dispersion_facturadora"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dispersion",
            name="total_honorarios",
        ),
    ]
