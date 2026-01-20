from datetime import date
from decimal import Decimal
from typing import Optional, Tuple
from django.utils import timezone
from dispersiones.models import Dispersion
from clientes.models import Cliente
from .models import Comision


def first_day_next_month(d: date) -> date:
    y, m = d.year, d.month
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)


def periodo_from_date(d: date) -> Tuple[int, int]:
    return d.month, d.year


def _normalize_razon_social(value: str) -> str:
    return " ".join(value.split()).strip().upper() if value else ""


def _all_dispersions_paid_group(cliente_ids: list[int], mes: int, anio: int) -> bool:
    qs = Dispersion.objects.filter(cliente_id__in=cliente_ids, fecha__year=anio, fecha__month=mes)
    total = qs.count()
    if total == 0:
        return False
    return qs.filter(estatus_pago="Pagado").count() == total


def evaluar_liberacion_grupo_mes(cliente_ids: list[int], mes: int, anio: int, today: Optional[date] = None) -> None:
    """
    Libera (o bloquea) todas las comisiones del grupo en el periodo dado
    si ya es mes vencido y todas las dispersiones del periodo estan Pagadas.
    """
    today = today or timezone.localdate()
    liberable_desde = first_day_next_month(date(anio, mes, 1))
    qs = Comision.objects.filter(cliente_id__in=cliente_ids, periodo_mes=mes, periodo_anio=anio)
    if not qs.exists():
        return
    liberar = today >= liberable_desde and _all_dispersions_paid_group(cliente_ids, mes, anio)
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
    cliente_ids = [cid for cid, _, _ in periodos]
    clientes = Cliente.objects.filter(id__in=cliente_ids).values("id", "razon_social")
    id_to_norm = {c["id"]: _normalize_razon_social(c["razon_social"] or "") for c in clientes}
    norm_to_ids: dict[str, list[int]] = {}
    for cid, norm in id_to_norm.items():
        norm_to_ids.setdefault(norm, []).append(cid)
    seen = set()
    today = today or timezone.localdate()
    for cliente_id, per_mes, per_anio in periodos:
        norm = id_to_norm.get(cliente_id, "")
        key = (norm, per_mes, per_anio)
        if key in seen:
            continue
        seen.add(key)
        evaluar_liberacion_grupo_mes(norm_to_ids.get(norm, [cliente_id]), per_mes, per_anio, today=today)
    return len(seen)


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
            monto = (Decimal(pct) * Decimal(instance.monto_dispersion or 0)).quantize(Decimal("0.01"))
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

    norm = _normalize_razon_social(cliente.razon_social or "")
    group_ids = list(
        Cliente.objects.filter(razon_social__iexact=cliente.razon_social).values_list("id", flat=True)
    )
    if not group_ids:
        group_ids = [cliente.id]
    evaluar_liberacion_grupo_mes(group_ids, periodo_mes, periodo_anio)
