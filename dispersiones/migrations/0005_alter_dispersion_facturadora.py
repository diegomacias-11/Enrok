from django.db import migrations, models

import core.choices


class Migration(migrations.Migration):

    dependencies = [
        ("dispersiones", "0004_alter_dispersion_facturadora_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dispersion",
            name="facturadora",
            field=models.CharField(
                blank=True,
                choices=core.choices.FACTURADORA_CHOICES,
                max_length=100,
                null=True,
            ),
        ),
    ]
