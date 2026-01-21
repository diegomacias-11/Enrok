from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q, Sum
from django.contrib.auth import get_user_model, models as auth_models
from django.contrib import messages
from .models import Dispersion
from core.choices import ESTATUS_PAGO_CHOICES, ESTATUS_PERIODO_CHOICES, ESTATUS_PROCESO_CHOICES
from .forms import DispersionForm
from clientes.models import Cliente


User = get_user_model()


def _user_in_groups(user, names):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return any(user.groups.filter(name__iexact=name).exists() for name in names)


def _can_ver_todos_clientes(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return (
        user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or user.groups.filter(name__iexact="Direccion Operaciones").exists()
        or user.groups.filter(name__iexact="Dirección Operaciones").exists()
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



def dispersiones_lista(request):
    is_contabilidad = (
        request.user.is_authenticated
        and not request.user.is_superuser
        and request.user.groups.filter(name__iexact="Contabilidad").exists()
    )

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    dispersiones = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("-fecha")
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False

    cliente_id = request.GET.get("cliente") or ""
    if is_contabilidad:
        is_ejecutivo = False
        ejecutivo_id = ""
        estatus_pago = ""
        factura_solicitada = ""
        dispersiones = dispersiones.filter(factura_solicitada=True).distinct()
        if cliente_id:
            dispersiones = dispersiones.filter(cliente_id=cliente_id)
        clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()
    else:
        ejecutivo_id = request.GET.get("ejecutivo") or ""
        if is_ejecutivo:
            puede_ver_todos = _can_ver_todos_clientes(request.user)
            dispersiones = dispersiones.filter(
                Q(cliente__ejecutivo=request.user)
                | Q(cliente__ejecutivo2=request.user)
                | Q(cliente__ejecutivo_apoyo=request.user)
                | Q(ejecutivo=request.user)
            ).distinct()
            if puede_ver_todos:
                dispersiones = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("-fecha")
            if cliente_id:
                dispersiones = dispersiones.filter(cliente_id=cliente_id)
            if puede_ver_todos:
                clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()
            else:
                clientes_qs = Cliente.objects.filter(
                    Q(ejecutivo=request.user)
                    | Q(ejecutivo2=request.user)
                    | Q(ejecutivo_apoyo=request.user)
                    | Q(dispersion__ejecutivo=request.user)
                ).filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()
            estatus_pago = ""
            factura_solicitada = request.GET.get("factura_solicitada") or ""
            if ejecutivo_id:
                dispersiones = dispersiones.filter(ejecutivo_id=ejecutivo_id)
            if factura_solicitada in ("0", "1"):
                dispersiones = dispersiones.filter(factura_solicitada=(factura_solicitada == "1"))
        else:
            estatus_pago = ""
            factura_solicitada = request.GET.get("factura_solicitada") or ""
            if ejecutivo_id:
                dispersiones = dispersiones.filter(ejecutivo_id=ejecutivo_id)
            if cliente_id:
                dispersiones = dispersiones.filter(cliente_id=cliente_id)
            if factura_solicitada in ("0", "1"):
                dispersiones = dispersiones.filter(factura_solicitada=(factura_solicitada == "1"))
            dispersiones = dispersiones.distinct()
            clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()

    # Nombre de mes en español
    meses_nombres = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    meses_choices = [(i, meses_nombres[i]) for i in range(1, 13)]
    ejecutivos_qs = (
        _users_in_group("Ejecutivo Jr")
        | _users_in_group("Ejecutivo Sr")
        | _users_in_group("Ejecutivo Apoyo")
    ).order_by("username").distinct()
    ejecutivos = [(u.id, _label_user(u)) for u in ejecutivos_qs]
    context = {
        "dispersiones": dispersiones,
        "mes": str(mes),
        "anio": str(anio),
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "mes_nombre": meses_nombres[mes],
        "is_contabilidad": is_contabilidad,
        "is_ejecutivo": is_ejecutivo,
        "ejecutivos": ejecutivos,
        "f_ejecutivo": ejecutivo_id,
        "f_cliente": cliente_id,
        "f_factura_solicitada": factura_solicitada,
        "f_estatus_pago": "",
        "estatus_pago_choices": ESTATUS_PAGO_CHOICES,
        "clientes": clientes_qs.order_by("razon_social"),
    }
    return render(request, "dispersiones/lista.html", context)


def dispersiones_kanban(request):
    if not request.user.is_authenticated:
        return redirect(reverse("login"))
    is_contabilidad = (
        request.user.is_authenticated
        and not request.user.is_superuser
        and request.user.groups.filter(name__iexact="Contabilidad").exists()
    )
    if not (
        request.user.is_superuser
        or request.user.groups.filter(name__iexact="Dirección Operaciones").exists()
        or request.user.groups.filter(name__iexact="Direccion Operaciones").exists()
        or request.user.groups.filter(name__iexact="Ejecutivo Sr").exists()
    ):
        return redirect(reverse("dispersiones_list"))

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    qs = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("-fecha")
    ejecutivo_id = request.GET.get("ejecutivo") or ""
    factura_solicitada = request.GET.get("factura_solicitada") or ""
    cliente_id = request.GET.get("cliente") or ""
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if ejecutivo_id:
        qs = qs.filter(ejecutivo_id=ejecutivo_id)
    if factura_solicitada in ("0", "1"):
        qs = qs.filter(factura_solicitada=(factura_solicitada == "1"))
    clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()
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
        | _users_in_group("Ejecutivo Apoyo")
    ).order_by("username").distinct()
    ejecutivos = [(u.id, _label_user(u)) for u in ejecutivos_qs]
    context = {
        "kanban_data": grouped,
        "mes": str(mes),
        "anio": str(anio),
        "mes_nombre": meses_nombres[mes],
        "is_contabilidad": is_contabilidad,
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "ejecutivos": ejecutivos,
        "f_ejecutivo": ejecutivo_id,
        "f_factura_solicitada": factura_solicitada,
        "clientes": clientes_qs.order_by("razon_social"),
        "f_cliente": cliente_id,
        "total_dispersiones": total_dispersiones,
        "total_dispersado": totals["total_dispersado"] or 0,
        "total_facturado": totals["total_facturado"] or 0,
    }
    return render(request, "dispersiones/kanban.html", context)


def dispersiones_kanban_ejecutivos(request):
    if not request.user.is_authenticated:
        return redirect(reverse("login"))
    is_contabilidad = (
        request.user.is_authenticated
        and not request.user.is_superuser
        and request.user.groups.filter(name__iexact="Contabilidad").exists()
    )
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    if is_contabilidad:
        return redirect(reverse("dispersiones_list"))
    if not (is_ejecutivo or request.user.is_superuser):
        return redirect(reverse("dispersiones_list"))

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    qs = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("-fecha")
    if is_ejecutivo and not request.user.is_superuser:
        puede_ver_todos = _can_ver_todos_clientes(request.user)
        if not puede_ver_todos:
            qs = qs.filter(
                Q(cliente__ejecutivo=request.user)
                | Q(cliente__ejecutivo2=request.user)
                | Q(cliente__ejecutivo_apoyo=request.user)
                | Q(ejecutivo=request.user)
            ).distinct()
            clientes_qs = Cliente.objects.filter(
                Q(ejecutivo=request.user)
                | Q(ejecutivo2=request.user)
                | Q(ejecutivo_apoyo=request.user)
                | Q(dispersion__ejecutivo=request.user)
            ).distinct()
        else:
            clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()
    else:
        clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio).distinct()
    ejecutivo_id = request.GET.get("ejecutivo") or ""
    factura_solicitada = request.GET.get("factura_solicitada") or ""
    cliente_id = request.GET.get("cliente") or ""
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if ejecutivo_id:
        qs = qs.filter(ejecutivo_id=ejecutivo_id)
    if factura_solicitada in ("0", "1"):
        qs = qs.filter(factura_solicitada=(factura_solicitada == "1"))
    totals = qs.aggregate(
        total_dispersado=Sum("monto_dispersion"),
        total_facturado=Sum("monto_comision_iva"),
    )
    total_dispersiones = qs.count()

    status_classes = {
        "Pendiente": "status-proceso-pendiente",
        "Enviada": "status-proceso-enviada",
        "Aplicada": "status-proceso-aplicada",
    }
    grouped = []
    proceso_order = [key for key, _ in ESTATUS_PROCESO_CHOICES]
    periodo_order = [key for key, _ in ESTATUS_PERIODO_CHOICES]
    for estatus in proceso_order:
        items_proceso = qs.filter(estatus_proceso=estatus)
        periodos = []
        for periodo in periodo_order:
            items_periodo = items_proceso.filter(estatus_periodo=periodo)
            if not items_periodo.exists():
                continue
            by_cliente = {}
            for d in items_periodo:
                key = (d.cliente.razon_social or "").strip().upper()
                if key not in by_cliente:
                    by_cliente[key] = []
                by_cliente[key].append(
                    {
                        "cliente": d.cliente.razon_social or "",
                        "id": d.id,
                        "monto": d.monto_comision,
                        "fecha": d.fecha,
                        "num_factura_honorarios": d.num_factura_honorarios,
                    }
                )
            clientes = [
                {"cliente": cliente or "Sin cliente", "items": regs}
                for cliente, regs in sorted(by_cliente.items())
            ]
            card_count = sum(len(grupo["items"]) for grupo in clientes)
            periodos.append({"titulo": periodo, "clientes": clientes, "card_count": card_count})
        total_count = sum(periodo["card_count"] for periodo in periodos)
        grouped.append(
            {
                "titulo": estatus,
                "status_class": status_classes.get(estatus, ""),
                "periodos": periodos,
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
        | _users_in_group("Ejecutivo Apoyo")
    ).order_by("username").distinct()
    ejecutivos = [(u.id, _label_user(u)) for u in ejecutivos_qs]
    context = {
        "kanban_data": grouped,
        "mes": str(mes),
        "anio": str(anio),
        "mes_nombre": meses_nombres[mes],
        "is_contabilidad": is_contabilidad,
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "ejecutivos": ejecutivos,
        "f_ejecutivo": ejecutivo_id,
        "f_factura_solicitada": factura_solicitada,
        "clientes": clientes_qs.order_by("razon_social"),
        "f_cliente": cliente_id,
        "total_dispersiones": total_dispersiones,
        "total_dispersado": totals["total_dispersado"] or 0,
        "total_facturado": totals["total_facturado"] or 0,
    }
    return render(request, "dispersiones/kanban_ejecutivos.html", context)


def dispersiones_kanban_contabilidad(request):
    if not request.user.is_authenticated:
        return redirect(reverse("login"))
    is_contabilidad = (
        request.user.is_authenticated
        and not request.user.is_superuser
        and request.user.groups.filter(name__iexact="Contabilidad").exists()
    )
    if not is_contabilidad:
        return redirect(reverse("dispersiones_list"))

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    cliente_id = request.GET.get("cliente") or ""
    qs = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio, factura_solicitada=True).order_by("-fecha")
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
    clientes_qs = Cliente.objects.filter(dispersion__fecha__month=mes, dispersion__fecha__year=anio, dispersion__factura_solicitada=True).distinct()
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
    return render(request, "dispersiones/kanban_contabilidad.html", context)


def agregar_dispersion(request):
    mes, anio, redir = _coerce_mes_anio(request)
    if redir and request.method != "POST":
        return redir
    back_url = request.GET.get("next") or f"{reverse('dispersiones_list')}?mes={mes}&anio={anio}"
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    is_contabilidad = (
        request.user.is_authenticated
        and not request.user.is_superuser
        and request.user.groups.filter(name__iexact="Contabilidad").exists()
    )
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
                    f"{reverse('dispersiones_edit', args=[disp.id])}?mes={mes}&anio={anio}&next={back_url}"
                )
            return redirect(request.POST.get("next") or back_url)
    else:
        form = DispersionForm(mes=mes, anio=anio, user=request.user)
    return render(
        request,
        "dispersiones/form.html",
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
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    is_apoyo = _user_in_groups(request.user, ["Ejecutivo Apoyo"])
    is_contabilidad = (
        request.user.is_authenticated
        and not request.user.is_superuser
        and request.user.groups.filter(name__iexact="Contabilidad").exists()
    )
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False
    if is_ejecutivo and not is_apoyo and not (
        disp.cliente.ejecutivo_id == request.user.id
        or disp.cliente.ejecutivo2_id == request.user.id
        or disp.cliente.ejecutivo_apoyo_id == request.user.id
        or disp.ejecutivo_id == request.user.id
    ):
        return redirect(reverse("dispersiones_list"))
    mes, anio, _ = _coerce_mes_anio(request)
    back_url = request.GET.get("next") or f"{reverse('dispersiones_list')}?mes={mes}&anio={anio}"
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
    template_name = "dispersiones/form_contabilidad.html" if is_contabilidad else "dispersiones/form.html"
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
    back_url = request.POST.get("next") or request.GET.get("next") or reverse("dispersiones_list")
    disp = get_object_or_404(Dispersion, pk=id)
    disp.delete()
    return redirect(back_url)
