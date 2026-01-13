from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from django.contrib.auth import get_user_model, models as auth_models
from .models import Dispersion
from core.choices import ESTATUS_PROCESO_CHOICES, ESTATUS_PAGO_CHOICES
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


def dispersiones_lista(request):
    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    dispersiones = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("fecha")
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False

    cliente_id = request.GET.get("cliente") or ""
    if is_ejecutivo:
        puede_ver_todos = _can_ver_todos_clientes(request.user)
        dispersiones = dispersiones.filter(
            Q(cliente__ejecutivo=request.user)
            | Q(cliente__ejecutivo2=request.user)
            | Q(cliente__ejecutivo_apoyo=request.user)
            | Q(ejecutivo=request.user)
        ).distinct()
        if puede_ver_todos:
            dispersiones = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("fecha")
        if cliente_id:
            dispersiones = dispersiones.filter(cliente_id=cliente_id)
        if puede_ver_todos:
            clientes_qs = Cliente.objects.all()
        else:
            clientes_qs = Cliente.objects.filter(
                Q(ejecutivo=request.user)
                | Q(ejecutivo2=request.user)
                | Q(ejecutivo_apoyo=request.user)
                | Q(dispersion__ejecutivo=request.user)
            ).distinct()
        ejecutivo_id = estatus_proceso = estatus_pago = ""
    else:
        ejecutivo_id = request.GET.get("ejecutivo") or ""
        estatus_proceso = request.GET.get("estatus_proceso") or ""
        estatus_pago = request.GET.get("estatus_pago") or ""
        if ejecutivo_id:
            dispersiones = dispersiones.filter(ejecutivo_id=ejecutivo_id)
        if cliente_id:
            dispersiones = dispersiones.filter(cliente_id=cliente_id)
        if estatus_proceso:
            dispersiones = dispersiones.filter(estatus_proceso=estatus_proceso)
        if estatus_pago:
            dispersiones = dispersiones.filter(estatus_pago=estatus_pago)
        dispersiones = dispersiones.distinct()
        clientes_qs = Cliente.objects.all()

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
        "is_ejecutivo": is_ejecutivo,
        "ejecutivos": ejecutivos,
        "f_ejecutivo": ejecutivo_id if not is_ejecutivo else "",
        "f_cliente": cliente_id,
        "f_estatus_proceso": estatus_proceso if not is_ejecutivo else "",
        "f_estatus_pago": estatus_pago if not is_ejecutivo else "",
        "estatus_proceso_choices": ESTATUS_PROCESO_CHOICES,
        "estatus_pago_choices": ESTATUS_PAGO_CHOICES,
        "clientes": clientes_qs.order_by("razon_social"),
    }
    return render(request, "dispersiones/lista.html", context)


def dispersiones_kanban(request):
    if not request.user.is_authenticated:
        return redirect(reverse("login"))
    if not (
        request.user.is_superuser
        or request.user.groups.filter(name__iexact="Dirección Operaciones").exists()
        or request.user.groups.filter(name__iexact="Direccion Operaciones").exists()
    ):
        return redirect(reverse("dispersiones_list"))

    mes, anio, redir = _coerce_mes_anio(request)
    if redir:
        return redir

    qs = Dispersion.objects.filter(fecha__month=mes, fecha__year=anio).order_by("fecha")

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
                    "monto": d.monto_dispersion,
                    "fecha": d.fecha,
                    "num_factura_honorarios": d.num_factura_honorarios,
                }
            )
        clientes = [
            {"cliente": cliente or "Sin cliente", "items": regs}
            for cliente, regs in sorted(by_cliente.items())
        ]
        grouped.append(
            {
                "titulo": estatus,
                "status_class": "status-pendiente" if estatus == "Pendiente" else "status-pagado",
                "clientes": clientes,
            }
        )

    meses_nombres = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    meses_choices = [(i, meses_nombres[i]) for i in range(1, 13)]
    context = {
        "kanban_data": grouped,
        "mes": str(mes),
        "anio": str(anio),
        "mes_nombre": meses_nombres[mes],
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
    }
    return render(request, "dispersiones/kanban.html", context)


def agregar_dispersion(request):
    mes, anio, redir = _coerce_mes_anio(request)
    if redir and request.method != "POST":
        return redir
    back_url = request.GET.get("next") or f"{reverse('dispersiones_list')}?mes={mes}&anio={anio}"
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False

    if request.method == "POST":
        mes = int(request.POST.get("mes") or mes or datetime.now().month)
        anio = int(request.POST.get("anio") or anio or datetime.now().year)
        form = DispersionForm(request.POST, mes=mes, anio=anio, user=request.user)
        if form.is_valid():
            disp = form.save()
            return redirect(request.POST.get("next") or back_url)
    else:
        form = DispersionForm(mes=mes, anio=anio, user=request.user)
    return render(request, "dispersiones/form.html", {"form": form, "back_url": back_url, "mes": mes, "anio": anio, "is_ejecutivo": is_ejecutivo, "cliente_info": form.cliente_info})


def editar_dispersion(request, id: int):
    disp = get_object_or_404(Dispersion, pk=id)
    is_ejecutivo = _user_in_groups(request.user, ["Ejecutivo Jr", "Ejecutivo Sr", "Ejecutivo Apoyo"])
    if request.user.is_authenticated and request.user.is_superuser:
        is_ejecutivo = False
    if is_ejecutivo and not (
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
            form.save()
            return redirect(request.POST.get("next") or back_url)
    else:
        form = DispersionForm(instance=disp, mes=mes, anio=anio, user=request.user)
    return render(request, "dispersiones/form.html", {"form": form, "dispersion": disp, "back_url": back_url, "mes": mes, "anio": anio, "is_ejecutivo": is_ejecutivo, "cliente_info": form.cliente_info})


def eliminar_dispersion(request, id: int):
    back_url = request.POST.get("next") or request.GET.get("next") or reverse("dispersiones_list")
    disp = get_object_or_404(Dispersion, pk=id)
    disp.delete()
    return redirect(back_url)
