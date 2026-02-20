from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q, Sum
from django.contrib.auth import get_user_model, models as auth_models
from django.contrib import messages
from .models import Dispersion
from core.choices import ESTATUS_PAGO_CHOICES
from .forms import DispersionForm
from clientes.models import Cliente


User = get_user_model()


def _user_in_groups(user, names):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return any(user.groups.filter(name__iexact=name).exists() for name in names)


def _is_contabilidad_servicios(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return user.groups.filter(name__iexact="Contabilidad Servicios").exists()


def _can_ver_todos_clientes(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return (
        user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or user.groups.filter(name__iexact="Ejecutivo Sr Servicios").exists()
        or user.groups.filter(name__iexact="Direccion Operaciones").exists()
        or user.groups.filter(name__iexact="Dirección Operaciones").exists()
    )


def _can_edit_estatus_pago(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return (
        user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or user.groups.filter(name__iexact="Ejecutivo Sr Servicios").exists()
        or user.groups.filter(name__iexact="Direccion Operaciones").exists()
        or user.groups.filter(name__iexact="Direcci?n Operaciones").exists()
    )



def _users_in_group(name: str):
    try:
        grupo = auth_models.Group.objects.get(name__iexact=name)
    except auth_models.Group.DoesNotExist:
        return User.objects.none()
    return grupo.user_set.all()


def _label_user(u):
    name = f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
    return name or getattr(u, "username", "")


def _coerce_mes_anio(request):
    now = datetime.now()
    mes = request.GET.get("mes")
    anio = request.GET.get("anio")
    if not mes or not anio:
        # Redirect preserving other query params
        return None, None, redirect(f"{request.path}?mes={now.month}&anio={now.year}")
    try:
        mes_i = int(mes)
        if mes_i < 1 or mes_i > 12:
            mes_i = now.month
    except (TypeError, ValueError):
        mes_i = now.month
    try:
        anio_i = int(anio)
    except (TypeError, ValueError):
        anio_i = now.year
    return mes_i, anio_i, None


def _coerce_mes_anio_kanban(request):
    now = datetime.now()
    mes_raw = (request.GET.get("mes") or "").strip()
    anio_raw = (request.GET.get("anio") or "").strip()
    if not mes_raw or not anio_raw:
        return None, None, None, redirect(f"{request.path}?mes={now.month}&anio={now.year}")

    mes_l = mes_raw.lower()
    if mes_l in ("all", "todos"):
        mes_i = None
        mes_param = "all"
    else:
        try:
            mes_i = int(mes_raw)
            if mes_i < 1 or mes_i > 12:
                mes_i = now.month
        except (TypeError, ValueError):
            mes_i = now.month
        mes_param = str(mes_i)

    try:
        anio_i = int(anio_raw)
    except (TypeError, ValueError):
        anio_i = now.year
    return mes_i, anio_i, mes_param, None


def _enrok_comision_monto(dispersion):
    total = Decimal("0")
    cliente = getattr(dispersion, "cliente", None)
    if not cliente:
        return total
    monto_base = Decimal(dispersion.monto_dispersion or 0)
    for i in range(1, 13):
        comisionista = getattr(cliente, f"comisionista{i}", None)
        pct = getattr(cliente, f"comision{i}", None)
        if not comisionista or pct is None:
            continue
        nombre = getattr(comisionista, "nombre", "")
        if str(nombre).strip().upper() == "ENROK":
            try:
                total += (Decimal(pct) * monto_base).quantize(Decimal("0.01"))
            except Exception:
                continue
    return total



def dispersiones_servicios_lista(request):
    is_contabilidad = _is_contabilidad_servicios(request.user)

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    dispersiones = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio)
    dia = (request.GET.get("dia") or "").strip()
    if dia:
        try:
            dia_i = int(dia)
            dispersiones = dispersiones.filter(fecha__day=dia_i)
        except (TypeError, ValueError):
            dia = ""
    dispersiones_periodo_qs = dispersiones
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Sr Servicios", "Ejecutivo Apoyo"])
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False

    cliente_id = request.GET.get("cliente") or ""
    ejecutivo_ids = []
    if is_contabilidad:
        is_ejecutivo = False
        factura_solicitada = ""
        dispersiones = dispersiones.filter(factura_solicitada=True).distinct()
        if cliente_id:
            dispersiones = dispersiones.filter(cliente_id=cliente_id)
        clientes_qs = Cliente.objects.filter(
            dispersiones_servicios__fecha__month=mes,
            dispersiones_servicios__fecha__year=anio,
            dispersiones_servicios__factura_solicitada=True,
        ).exclude(servicio__in=["PROCOM", "PRAIDS"]).distinct()
    else:
        ejecutivo_ids_raw = request.GET.getlist("ejecutivo")
        ejecutivo_ids = [e for e in ejecutivo_ids_raw if str(e).strip()]
        if is_ejecutivo:
            puede_ver_todos = _can_ver_todos_clientes(request.user)
            dispersiones = dispersiones.filter(
                Q(cliente__ejecutivo=request.user)
                | Q(cliente__ejecutivo2=request.user)
                | Q(cliente__ejecutivo_apoyo=request.user)
                | Q(ejecutivo=request.user)
            ).distinct()
            if puede_ver_todos:
                dispersiones = dispersiones_periodo_qs
            if cliente_id:
                dispersiones = dispersiones.filter(cliente_id=cliente_id)
            if puede_ver_todos:
                clientes_qs = Cliente.objects.filter(
                    dispersiones_servicios__fecha__month=mes,
                    dispersiones_servicios__fecha__year=anio,
                ).exclude(servicio__in=["PROCOM", "PRAIDS"]).distinct()
            else:
                clientes_qs = Cliente.objects.filter(
                    Q(ejecutivo=request.user)
                    | Q(ejecutivo2=request.user)
                    | Q(ejecutivo_apoyo=request.user)
                    | Q(dispersiones_servicios__ejecutivo=request.user)
            ).filter(
                dispersiones_servicios__fecha__month=mes,
                dispersiones_servicios__fecha__year=anio,
            ).exclude(servicio__in=["PROCOM", "PRAIDS"]).distinct()
            factura_solicitada = request.GET.get("factura_solicitada") or ""
            dispersiones_servicios_base = dispersiones
            if ejecutivo_ids:
                dispersiones = dispersiones.filter(ejecutivo_id__in=ejecutivo_ids)
            if factura_solicitada in ("0", "1"):
                dispersiones = dispersiones.filter(factura_solicitada=(factura_solicitada == "1"))
        else:
            factura_solicitada = request.GET.get("factura_solicitada") or ""
            dispersiones_servicios_base = dispersiones
            if ejecutivo_ids:
                dispersiones = dispersiones.filter(ejecutivo_id__in=ejecutivo_ids)
            if cliente_id:
                dispersiones = dispersiones.filter(cliente_id=cliente_id)
            if factura_solicitada in ("0", "1"):
                dispersiones = dispersiones.filter(factura_solicitada=(factura_solicitada == "1"))
            dispersiones = dispersiones.distinct()
            clientes_qs = Cliente.objects.filter(
                dispersiones_servicios__fecha__month=mes,
                dispersiones_servicios__fecha__year=anio,
            ).exclude(servicio__in=["PROCOM", "PRAIDS"]).distinct()

    # Nombre de mes en español
    meses_nombres = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    meses_choices = [(i, meses_nombres[i]) for i in range(1, 13)]
    dispersiones_servicios_base = locals().get("dispersiones_servicios_base", dispersiones)
    ejecutivos = []
    if not is_contabilidad:
        exec_rows = (
            dispersiones_servicios_base.exclude(ejecutivo__isnull=True)
            .values("ejecutivo_id", "ejecutivo__first_name", "ejecutivo__last_name", "ejecutivo__username")
            .distinct()
            .order_by("ejecutivo__username")
        )
        for row in exec_rows:
            exec_id = row.get("ejecutivo_id")
            if not exec_id:
                continue
            name = f"{row.get('ejecutivo__first_name', '')} {row.get('ejecutivo__last_name', '')}".strip()
            label = name or (row.get("ejecutivo__username") or "")
            ejecutivos.append((exec_id, label))

    orden = request.GET.get("orden") or "reciente"
    if orden == "antigua":
        dispersiones = dispersiones.order_by("fecha", "id")
    elif orden == "az":
        dispersiones = dispersiones.order_by("cliente__razon_social", "id")
    elif orden == "za":
        dispersiones = dispersiones.order_by("-cliente__razon_social", "-id")
    else:
        orden = "reciente"
        dispersiones = dispersiones.order_by("-fecha", "-id")

    context = {
        "dispersiones": dispersiones,
        "mes": str(mes),
        "anio": str(anio),
        "f_dia": dia,
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "mes_nombre": meses_nombres[mes],
        "is_contabilidad": is_contabilidad,
        "is_ejecutivo": is_ejecutivo,
        "ejecutivos": ejecutivos,
        "f_ejecutivo": ejecutivo_ids,
        "f_cliente": cliente_id,
        "f_factura_solicitada": factura_solicitada,
        "f_orden": orden,
        "f_estatus_pago": "",
        "estatus_pago_choices": ESTATUS_PAGO_CHOICES,
        "clientes": clientes_qs.order_by("razon_social"),
    }
    return render(request, "dispersiones_servicios/lista.html", context)


def dispersiones_servicios_kanban(request):
    if not request.user.is_authenticated:
        return redirect(reverse("login"))
    is_contabilidad = _is_contabilidad_servicios(request.user)
    if not (
        request.user.is_superuser
        or request.user.groups.filter(name__iexact="Dirección Operaciones").exists()
        or request.user.groups.filter(name__iexact="Direccion Operaciones").exists()
        or request.user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or request.user.groups.filter(name__iexact="Ejecutivo Sr Servicios").exists()
    ):
        return redirect(reverse("dispersiones_servicios_list"))

    mes, anio, mes_param, redir = _coerce_mes_anio_kanban(request)
    if redir:
        return redir

    qs = Dispersion.objects.filter(fecha__year=anio)
    if mes is not None:
        qs = qs.filter(fecha__month=mes)
    qs = qs.order_by("-fecha", "-id")
    dia = (request.GET.get("dia") or "").strip()
    if dia:
        try:
            dia_i = int(dia)
            qs = qs.filter(fecha__day=dia_i)
        except (TypeError, ValueError):
            dia = ""
    ejecutivo_ids_raw = request.GET.getlist("ejecutivo")
    ejecutivo_ids = [e for e in ejecutivo_ids_raw if str(e).strip()]
    factura_solicitada = request.GET.get("factura_solicitada") or ""
    cliente_id = request.GET.get("cliente") or ""
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if ejecutivo_ids:
        qs = qs.filter(ejecutivo_id__in=ejecutivo_ids)
    if factura_solicitada in ("0", "1"):
        qs = qs.filter(factura_solicitada=(factura_solicitada == "1"))
    clientes_qs = Cliente.objects.filter(
        dispersiones_servicios__fecha__year=anio,
    ).exclude(servicio__in=["PROCOM", "PRAIDS"])
    if mes is not None:
        clientes_qs = clientes_qs.filter(dispersiones_servicios__fecha__month=mes)
    clientes_qs = clientes_qs.distinct()
    totals = qs.aggregate(
        total_dispersado=Sum("monto_dispersion"),
        total_facturado=Sum("monto_comision_iva"),
    )
    total_dispersiones = qs.count()

    grouped = []
    for estatus in ("Pendiente", "Pagado"):
        items = qs.filter(estatus_pago=estatus)
        by_cliente = {}
        for d in items:
            key = (d.cliente.razon_social or "").strip().upper()
            if key not in by_cliente:
                by_cliente[key] = []
            by_cliente[key].append(
                {
                    "cliente": d.cliente.razon_social or "",
                    "id": d.id,
                    "monto": d.monto_comision_iva,
                    "monto_enrok": _enrok_comision_monto(d),
                    "fecha": d.fecha,
                }
            )
        clientes = [
            {"cliente": cliente or "Sin cliente", "items": regs, "card_count": len(regs)}
            for cliente, regs in sorted(by_cliente.items())
        ]
        total_count = sum(c["card_count"] for c in clientes)
        grouped.append(
            {
                "titulo": estatus,
                "status_class": "status-pendiente" if estatus == "Pendiente" else "status-pagado",
                "clientes": clientes,
                "card_count": total_count,
            }
        )

    meses_nombres = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    meses_choices = [(i, meses_nombres[i]) for i in range(1, 13)]
    ejecutivos_qs = (
        _users_in_group("Ejecutivo Jr")
        | _users_in_group("Ejecutivo Sr")
        | _users_in_group("Ejecutivo Sr Servicios")
        | _users_in_group("Ejecutivo Apoyo")
    ).order_by("username").distinct()
    ejecutivos = [(u.id, _label_user(u)) for u in ejecutivos_qs]
    context = {
        "kanban_data": grouped,
        "mes": mes_param,
        "anio": str(anio),
        "f_dia": dia,
        "mes_nombre": "Todos" if mes is None else meses_nombres[mes],
        "is_contabilidad": is_contabilidad,
        "mes_all": mes is None,
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "ejecutivos": ejecutivos,
        "f_ejecutivo": ejecutivo_ids,
        "clientes": clientes_qs.order_by("razon_social"),
        "f_cliente": cliente_id,
        "f_factura_solicitada": factura_solicitada,
        "total_dispersiones": total_dispersiones,
        "total_dispersado": totals["total_dispersado"] or 0,
        "total_facturado": totals["total_facturado"] or 0,
    }
    return render(request, "dispersiones_servicios/kanban.html", context)


def dispersiones_servicios_kanban_contabilidad(request):
    if not request.user.is_authenticated:
        return redirect(reverse("login"))
    is_contabilidad = _is_contabilidad_servicios(request.user)
    if not is_contabilidad:
        return redirect(reverse("dispersiones_servicios_list"))

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    cliente_id = request.GET.get("cliente") or ""
    qs = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio, factura_solicitada=True).order_by("-fecha", "-id")
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)

    grouped = []
    pendientes_qs = qs.filter(Q(num_factura_honorarios__isnull=True) | Q(num_factura_honorarios=""))
    completadas_qs = qs.exclude(Q(num_factura_honorarios__isnull=True) | Q(num_factura_honorarios=""))
    for titulo, items in (("Pendientes", pendientes_qs), ("Completadas", completadas_qs)):
        by_cliente = {}
        for d in items:
            key = (d.cliente.razon_social or "").strip().upper()
            if key not in by_cliente:
                by_cliente[key] = []
            by_cliente[key].append(
                {
                    "cliente": d.cliente.razon_social or "",
                    "id": d.id,
                    "monto": d.monto_comision_iva,
                    "fecha": d.fecha,
                    "forma_pago": d.get_forma_pago_display() if hasattr(d, "get_forma_pago_display") else (d.forma_pago or ""),
                    "num_factura_honorarios": d.num_factura_honorarios,
                }
            )
        clientes = [
            {"cliente": cliente or "Sin cliente", "items": regs, "card_count": len(regs)}
            for cliente, regs in sorted(by_cliente.items())
        ]
        total_count = sum(c["card_count"] for c in clientes)
        grouped.append(
            {
                "titulo": titulo,
                "status_class": "status-pendiente" if titulo == "Pendientes" else "status-pagado",
                "clientes": clientes,
                "card_count": total_count,
            }
        )

    meses_nombres = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    meses_choices = [(i, meses_nombres[i]) for i in range(1, 13)]
    clientes_qs = Cliente.objects.filter(
        dispersiones_servicios__fecha__month=mes,
        dispersiones_servicios__fecha__year=anio,
        dispersiones_servicios__factura_solicitada=True,
    ).exclude(servicio__in=["PROCOM", "PRAIDS"]).distinct()
    context = {
        "kanban_data": grouped,
        "mes": str(mes),
        "anio": str(anio),
        "mes_nombre": meses_nombres[mes],
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "clientes": clientes_qs.order_by("razon_social"),
        "f_cliente": cliente_id,
    }
    return render(request, "dispersiones_servicios/kanban_contabilidad.html", context)


def agregar_dispersion(request):
    mes, anio, redir = _coerce_mes_anio(request)
    if redir and request.method != "POST":
        return redir
    back_url = request.GET.get("next") or f"{reverse('dispersiones_servicios_list')}?mes={mes}&anio={anio}"
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Sr Servicios", "Ejecutivo Apoyo"])
    is_contabilidad = _is_contabilidad_servicios(request.user)
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False
    if is_contabilidad:
        return redirect(back_url)

    if request.method == "POST":
        mes = int(request.POST.get("mes") or mes or datetime.now().month)
        anio = int(request.POST.get("anio") or anio or datetime.now().year)
        form = DispersionForm(request.POST, mes=mes, anio=anio, user=request.user)
        if form.is_valid():
            disp = form.save()
            sheets_error = getattr(disp, "_sheets_error", "")
            if sheets_error:
                messages.error(request, f"Sheets: {sheets_error}")
                return redirect(
                    f"{reverse('dispersiones_servicios_edit', args=[disp.id])}?mes={mes}&anio={anio}&next={back_url}"
                )
            return redirect(request.POST.get("next") or back_url)
    else:
        form = DispersionForm(mes=mes, anio=anio, user=request.user)
    return render(
        request,
        "dispersiones_servicios/form.html",
        {
            "form": form,
            "back_url": back_url,
            "mes": mes,
            "anio": anio,
            "is_ejecutivo": is_ejecutivo,
            "is_contabilidad": is_contabilidad,
            "cliente_info": form.cliente_info,
        },
    )


def editar_dispersion(request, id: int):
    disp = get_object_or_404(Dispersion, pk=id)
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Sr Servicios", "Ejecutivo Apoyo"])
    is_apoyo = _user_in_groups(request.user, ["Ejecutivo Apoyo"])
    is_contabilidad = _is_contabilidad_servicios(request.user)
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False
    if is_ejecutivo and not is_apoyo and not _can_edit_estatus_pago(request.user) and not (
        disp.cliente.ejecutivo_id == request.user.id
        or disp.cliente.ejecutivo2_id == request.user.id
        or disp.cliente.ejecutivo_apoyo_id == request.user.id
        or disp.ejecutivo_id == request.user.id
    ):
        return redirect(reverse("dispersiones_servicios_list"))
    mes, anio, _ = _coerce_mes_anio(request)
    back_url = request.GET.get("next") or f"{reverse('dispersiones_servicios_list')}?mes={mes}&anio={anio}"
    if request.method == "POST":
        form = DispersionForm(request.POST, instance=disp, mes=mes, anio=anio, user=request.user)
        if form.is_valid():
            disp = form.save()
            sheets_error = getattr(disp, "_sheets_error", "")
            if sheets_error:
                messages.error(request, f"Sheets: {sheets_error}")
                return redirect(request.path + f"?mes={mes}&anio={anio}&next={back_url}")
            if getattr(disp, "_sheets_success", False):
                label = "CONDEFIN" if getattr(disp.cliente, "ac", "") == "CONFEDIN" else "RESTO DE AC"
                messages.success(request, f"Factura enviada a {label}.")
            return redirect(request.POST.get("next") or back_url)
    else:
        form = DispersionForm(instance=disp, mes=mes, anio=anio, user=request.user)
    template_name = "dispersiones_servicios/form_contabilidad.html" if is_contabilidad else "dispersiones_servicios/form.html"
    return render(
        request,
        template_name,
        {
            "form": form,
            "dispersion": disp,
            "back_url": back_url,
            "mes": mes,
            "anio": anio,
            "is_ejecutivo": is_ejecutivo,
            "is_contabilidad": is_contabilidad,
            "cliente_info": form.cliente_info,
        },
    )


def eliminar_dispersion(request, id: int):
    back_url = request.POST.get("next") or request.GET.get("next") or reverse("dispersiones_servicios_list")
    disp = get_object_or_404(Dispersion, pk=id)
    disp.delete()
    return redirect(back_url)
