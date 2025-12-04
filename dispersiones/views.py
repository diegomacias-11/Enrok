from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from .models import Dispersion
from .forms import DispersionForm
from clientes.models import Cliente


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
    is_ejecutivo = request.user.groups.filter(name__iexact="Ejecutivo").exists() if request.user.is_authenticated else False

    cliente_id = request.GET.get("cliente") or ""
    if is_ejecutivo:
        dispersiones = dispersiones.filter(
            Q(cliente__ejecutivo=request.user) | Q(cliente__ejecutivos_apoyo=request.user)
        ).distinct()
        if cliente_id:
            dispersiones = dispersiones.filter(cliente_id=cliente_id)
        clientes_qs = Cliente.objects.filter(
            Q(ejecutivo=request.user) | Q(ejecutivos_apoyo=request.user)
        ).distinct()
        ejecutivo_id = apoyo_id = estatus_proceso = estatus_pago = ""
    else:
        ejecutivo_id = request.GET.get("ejecutivo") or ""
        apoyo_id = request.GET.get("apoyo") or ""
        estatus_proceso = request.GET.get("estatus_proceso") or ""
        estatus_pago = request.GET.get("estatus_pago") or ""
        if ejecutivo_id:
            dispersiones = dispersiones.filter(cliente__ejecutivo_id=ejecutivo_id)
        if apoyo_id:
            dispersiones = dispersiones.filter(cliente__ejecutivos_apoyo__id=apoyo_id)
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
    ejecutivos = Cliente.objects.values_list("ejecutivo_id", "ejecutivo__username").exclude(ejecutivo_id=None).distinct()
    apoyos = Cliente.objects.values_list("ejecutivos_apoyo__id", "ejecutivos_apoyo__username").exclude(ejecutivos_apoyo__id=None).distinct()
    context = {
        "dispersiones": dispersiones,
        "mes": str(mes),
        "anio": str(anio),
        "meses": list(range(1, 13)),
        "meses_choices": meses_choices,
        "mes_nombre": meses_nombres[mes],
        "is_ejecutivo": is_ejecutivo,
        "ejecutivos": ejecutivos,
        "apoyos": apoyos,
        "f_ejecutivo": ejecutivo_id if not is_ejecutivo else "",
        "f_apoyo": apoyo_id if not is_ejecutivo else "",
        "f_cliente": cliente_id,
        "f_estatus_proceso": estatus_proceso if not is_ejecutivo else "",
        "f_estatus_pago": estatus_pago if not is_ejecutivo else "",
        "estatus_proceso_choices": Dispersion.EstatusProceso.choices,
        "estatus_pago_choices": Dispersion.EstatusPago.choices,
        "clientes": clientes_qs.order_by("razon_social"),
    }
    return render(request, "dispersiones/lista.html", context)


def agregar_dispersion(request):
    mes, anio, redir = _coerce_mes_anio(request)
    if redir and request.method != "POST":
        return redir
    back_url = request.GET.get("next") or f"{reverse('dispersiones_lista')}?mes={mes}&anio={anio}"
    is_ejecutivo = request.user.groups.filter(name__iexact="Ejecutivo").exists() if request.user.is_authenticated else False

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
    is_ejecutivo = request.user.groups.filter(name__iexact="Ejecutivo").exists() if request.user.is_authenticated else False
    if is_ejecutivo and not (disp.cliente.ejecutivo_id == request.user.id or disp.cliente.ejecutivos_apoyo.filter(id=request.user.id).exists()):
        return redirect(reverse("dispersiones_lista"))
    mes, anio, _ = _coerce_mes_anio(request)
    back_url = request.GET.get("next") or f"{reverse('dispersiones_lista')}?mes={mes}&anio={anio}"
    if request.method == "POST":
        form = DispersionForm(request.POST, instance=disp, mes=mes, anio=anio, user=request.user)
        if form.is_valid():
            form.save()
            return redirect(request.POST.get("next") or back_url)
    else:
        form = DispersionForm(instance=disp, mes=mes, anio=anio, user=request.user)
    return render(request, "dispersiones/form.html", {"form": form, "dispersion": disp, "back_url": back_url, "mes": mes, "anio": anio, "is_ejecutivo": is_ejecutivo, "cliente_info": form.cliente_info})


def eliminar_dispersion(request, id: int):
    back_url = request.POST.get("next") or request.GET.get("next") or reverse("dispersiones_lista")
    disp = get_object_or_404(Dispersion, pk=id)
    disp.delete()
    return redirect(back_url)
