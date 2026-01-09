from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dispersiones", "0005_alter_dispersion_facturadora"),
    ]

    operations = [
        migrations.AddField(
            model_name="dispersion",
            name="ejecutivo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="dispersiones_ejecutivo",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="dispersion",
            name="ejecutivo2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="dispersiones_ejecutivo2",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="dispersion",
            name="ejecutivo_apoyo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="dispersiones_apoyo",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
