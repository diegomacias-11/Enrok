from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clientes", "0006_alter_cliente_servicio"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="ejecutivos_apoyo",
            field=models.ManyToManyField(
                blank=True,
                related_name="clientes_apoyo",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
