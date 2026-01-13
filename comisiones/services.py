from datetime import date
from decimal import Decimal
from typing import Optional, Tuple
from django.utils import timezone
from dispersiones.models import Dispersion
from .models import Comision


def first_day_next_month(d: date) -> date:
    y, m = d.year, d.month
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)


def periodo_from_date(d: date) -> Tuple[int, int]:
    return d.month, d.year


def _all_dispersions_paid(cliente_id: int, mes: int, anio: int) -> bool:
    qs = Dispersion.objects.filter(cliente_id=cliente_id, fecha__year=anio, fecha__month=mes)
    total = qs.count()
    if total == 0:
        return False
    return qs.filter(estatus_pago="Pagado").count() == total


def evaluar_liberacion_cliente_mes(cliente_id: int, mes: int, anio: int, today: Optional[date] = None) -> None:
    """
    Libera (o bloquea) todas las comisiones del cliente en el periodo dado
    si ya es mes vencido y todas las dispersiones del periodo estan Pagadas.
    """
    today = today or timezone.localdate()
    liberable_desde = first_day_next_month(date(anio, mes, 1))
    qs = Comision.objects.filter(cliente_id=cliente_id, periodo_mes=mes, periodo_anio=anio)
    if not qs.exists():
        return
    liberar = today >= liberable_desde and _all_dispersions_paid(cliente_id, mes, anio)
    qs.update(liberada=liberar)


def recalcular_periodo(mes: int, anio: int, today: Optional[date] = None, solo_pendientes: bool = False) -> int:
    """
    Recalcula liberaciones para todos los clientes con comisiones en el periodo.
    Returna la cantidad de periodos cliente procesados.
    """
    qs = Comision.objects.filter(periodo_mes=mes, periodo_anio=anio)
    if solo_pendientes:
        qs = qs.filter(liberada=False)
    periodos = qs.values_list("cliente_id", "periodo_mes", "periodo_anio").distinct()
    today = today or timezone.localdate()
    for cliente_id, per_mes, per_anio in periodos:
        evaluar_liberacion_cliente_mes(cliente_id, per_mes, per_anio, today=today)
    return len(periodos)


def generar_comisiones_para_dispersion(instance: Dispersion) -> None:
    """
    Regenera las comisiones ligadas a una dispersion y aplica la regla
    de liberacion a mes vencido.
    """
    Comision.objects.filter(dispersion=instance).delete()

    cliente = instance.cliente
    periodo_mes, periodo_anio = periodo_from_date(instance.fecha)
    liberable_desde = first_day_next_month(instance.fecha)

    for i in range(1, 13):
        com_field = f"comisionista{i}"
        pct_field = f"comision{i}"
        comisionista = getattr(cliente, com_field, None)
        pct = getattr(cliente, pct_field, None)
        if comisionista and pct is not None and Decimal(pct) > 0:
            monto_base = Decimal(instance.monto_comision or 0)
            monto = (Decimal(pct) * monto_base).quantize(Decimal("0.01"))
            Comision.objects.create(
                dispersion=instance,
                cliente=cliente,
                comisionista=comisionista,
                servicio=getattr(instance, "servicio", ""),
                porcentaje=Decimal(pct),
                monto=monto,
                periodo_mes=periodo_mes,
                periodo_anio=periodo_anio,
                liberable_desde=liberable_desde,
                liberada=False,
                estatus_pago_dispersion=getattr(instance, "estatus_pago", ""),
                fecha_dispersion=instance.fecha,
            )

    evaluar_liberacion_cliente_mes(cliente.id, periodo_mes, periodo_anio)
