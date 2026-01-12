from django.conf import settings
from django.db import migrations, models


def forwards_copy_apoyo(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    for cliente in Cliente.objects.all():
        if cliente.ejecutivo_apoyo_id:
            continue
        try:
            apoyo = cliente.ejecutivos_apoyo.first()
        except Exception:
            apoyo = None
        if apoyo:
            cliente.ejecutivo_apoyo_id = apoyo.id
            cliente.save(update_fields=["ejecutivo_apoyo"])


def reverse_copy_apoyo(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    for cliente in Cliente.objects.all():
        apoyo = getattr(cliente, "ejecutivo_apoyo", None)
        if apoyo:
            try:
                cliente.ejecutivos_apoyo.add(apoyo)
            except Exception:
                continue


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0013_cliente_ejecutivo2"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="ejecutivo_apoyo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="clientes_apoyo",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(forwards_copy_apoyo, reverse_copy_apoyo),
        migrations.RemoveField(
            model_name="cliente",
            name="ejecutivos_apoyo",
        ),
    ]
