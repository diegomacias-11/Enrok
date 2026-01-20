from django.contrib import admin

from .models import Comision, PagoComision


@admin.register(Comision)
class ComisionAdmin(admin.ModelAdmin):
    list_display = ("comisionista", "cliente", "periodo_mes", "periodo_anio", "monto", "liberada")
    list_filter = ("periodo_mes", "periodo_anio", "liberada")
    search_fields = ("comisionista__nombre", "cliente__razon_social")


@admin.register(PagoComision)
class PagoComisionAdmin(admin.ModelAdmin):
    list_display = ("comisionista", "periodo_mes", "periodo_anio", "monto", "fecha_pago")
    list_filter = ("periodo_mes", "periodo_anio")
    search_fields = ("comisionista__nombre",)
