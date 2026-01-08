from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Cliente
from core.choices import SERVICIO_CHOICES
from .forms import ClienteForm
from django.contrib import messages
from decimal import Decimal


def clientes_lista(request):
    q = (request.GET.get("q") or "").strip()
    servicio = (request.GET.get("servicio") or "").strip()
    qs = Cliente.objects.all()
    if q:
        qs = qs.filter(razon_social__icontains=q)
    if servicio:
        qs = qs.filter(servicio=servicio)
    clientes = qs.order_by("razon_social")

    context = {"clientes": clientes, "q": q, "servicio": servicio, "servicio_choices": SERVICIO_CHOICES}
    return render(request, "clientes/lista.html", context)


def agregar_cliente(request):
    back_url = request.GET.get("next") or reverse("clientes_list")
    if request.method == "POST":
        back_url = request.POST.get("next") or back_url
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(back_url)
    else:
        form = ClienteForm()
    return render(request, "clientes/form.html", {"form": form, "back_url": back_url})


def editar_cliente(request, id: int):
    cliente = get_object_or_404(Cliente, pk=id)
    back_url = request.GET.get("next") or reverse("clientes_list")
    if request.method == "POST":
        back_url = request.POST.get("next") or back_url
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect(back_url)
    else:
        form = ClienteForm(instance=cliente)
        # Quitar advertencia en GET: ahora la validación se hace en el formulario y bloquea guardado
    return render(request, "clientes/form.html", {"form": form, "cliente": cliente, "back_url": back_url})


def eliminar_cliente(request, id: int):
    back_url = request.POST.get("next") or request.GET.get("next") or reverse("clientes_list")
    cliente = get_object_or_404(Cliente, pk=id)
    cliente.delete()
    return redirect(back_url)
