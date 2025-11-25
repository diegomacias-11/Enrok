from datetime import date
from calendar import monthrange
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from dispersiones.models import Dispersion
from .models import Comision


def first_day_next_month(d: date) -> date:
    y, m = d.year, d.month
    if m == 12:
        return date(y + 1, 1, 1)
    return date(y, m + 1, 1)


@receiver(post_save, sender=Dispersion)
def generar_comisiones(sender, instance: Dispersion, created, **kwargs):
    # Borra y regenera las comisiones de esta dispersión para reflejar cambios
    Comision.objects.filter(dispersion=instance).delete()

    cliente = instance.cliente
    # Tasa base ya calculada en monto_comision dentro de Dispersion
    monto_comision = instance.monto_comision

    # Mes/año del periodo
    periodo_mes = instance.fecha.month
    periodo_anio = instance.fecha.year
    liberable_desde = first_day_next_month(instance.fecha)

    # Iterar sobre 10 posibles comisionistas
    for i in range(1, 11):
        com_field = f"comisionista{i}"
        pct_field = f"comision{i}"
        comisionista = getattr(cliente, com_field, None)
        pct = getattr(cliente, pct_field, None)
        if comisionista and pct is not None and Decimal(pct) > 0:
            # Nuevo cálculo: porcentaje absoluto sobre el monto de dispersión
            monto = (Decimal(pct) * Decimal(instance.monto_dispersion)).quantize(Decimal('0.01'))
            liberada = str(getattr(instance, 'estatus_pago', '')) == 'Pagado'
            Comision.objects.create(
                dispersion=instance,
                cliente=cliente,
                comisionista=comisionista,
                servicio=getattr(instance, 'servicio', ''),
                porcentaje=Decimal(pct),
                monto=monto,
                periodo_mes=periodo_mes,
                periodo_anio=periodo_anio,
                liberable_desde=liberable_desde,
                liberada=liberada,
                estatus_pago_dispersion=getattr(instance, 'estatus_pago', ''),
                fecha_dispersion=instance.fecha,
            )
