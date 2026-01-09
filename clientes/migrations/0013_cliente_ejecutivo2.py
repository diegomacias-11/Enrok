from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clientes", "0012_alter_cliente_ac"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="ejecutivo2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="clientes_ejecutivo2",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
