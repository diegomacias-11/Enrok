from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clientes", "0007_cliente_ejecutivos_apoyo"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="ac",
            field=models.CharField(
                choices=[
                    ("CONFEDIN", "CONFEDIN"),
                    ("CAMARENCE", "CAMARENCE"),
                    ("SERVIARUGA", "SERVIARUGA"),
                    ("ZAMORA", "ZAMORA"),
                    ("INACTIVO", "INACTIVO"),
                ],
                default="CONFEDIN",
                max_length=20,
            ),
        ),
    ]
