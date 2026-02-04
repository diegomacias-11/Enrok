from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dispersiones_servicios", "0013_alter_dispersion_relations"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dispersion",
            name="factura_solicitada",
        ),
    ]
