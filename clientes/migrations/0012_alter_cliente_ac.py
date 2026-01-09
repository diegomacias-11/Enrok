from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clientes", "0011_alter_cliente_servicio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cliente",
            name="ac",
            field=models.CharField(blank=True, choices=[("CONFEDIN", "CONFEDIN"), ("CAMARENCE", "CAMARENCE"), ("SERVIARUGA", "SERVIARUGA"), ("ZAMORA", "ZAMORA"), ("INACTIVO", "INACTIVO")], max_length=20, null=True),
        ),
    ]
