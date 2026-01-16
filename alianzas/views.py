from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from .models import Alianza
from .forms import AlianzaForm
from clientes.models import Cliente


def alianzas_lista(request):
    q = (request.GET.get("q") or "").strip()
    alianzas_qs = Alianza.objects.all()
    if q:
        alianzas_qs = alianzas_qs.filter(nombre__icontains=q)
    alianzas = alianzas_qs.order_by("nombre")

    context = {
        "alianzas": alianzas,
        "q": q,
    }
    return render(request, "alianzas/lista.html", context)


def agregar_alianza(request):
    back_url = request.GET.get("next") or reverse("alianzas_list")

    if request.method == "POST":
        back_url = request.POST.get("next") or back_url
        form = AlianzaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(back_url)
    else:
        form = AlianzaForm()

    context = {
        "form": form,
        "back_url": back_url,
    }
    return render(request, "alianzas/form.html", context)


def editar_alianza(request, id: int):
    alianza = get_object_or_404(Alianza, pk=id)
    back_url = request.GET.get("next") or reverse("alianzas_list")
    clientes_rel = Cliente.objects.none()

    if request.method == "POST":
        back_url = request.POST.get("next") or back_url
        form = AlianzaForm(request.POST, instance=alianza)
        if form.is_valid():
            form.save()
            return redirect(back_url)
    else:
        form = AlianzaForm(instance=alianza)
        q = Q()
        for i in range(1, 13):
            q |= Q(**{f"comisionista{i}": alianza})
        clientes_rel = Cliente.objects.filter(q).order_by("razon_social")

    context = {
        "form": form,
        "alianza": alianza,
        "back_url": back_url,
        "clientes_rel": clientes_rel,
    }
    return render(request, "alianzas/form.html", context)


def eliminar_alianza(request, id: int):
    back_url = request.POST.get("next") or request.GET.get("next") or reverse("alianzas_list")
    alianza = get_object_or_404(Alianza, pk=id)
    alianza.delete()
    return redirect(back_url)
