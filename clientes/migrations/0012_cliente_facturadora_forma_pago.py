from django.db import migrations, models
import core.choices


class Migration(migrations.Migration):

    dependencies = [
        ("clientes", "0011_alter_cliente_servicio"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="facturadora",
            field=models.CharField(blank=True, choices=core.choices.FACTURADORA_CHOICES, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="cliente",
            name="forma_pago",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
