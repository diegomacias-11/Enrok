from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clientes", "0004_alter_cliente_servicio"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="ejecutivo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="clientes_ejecutivo",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
