from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "servicio", "ejecutivo", "fecha_registro")
    search_fields = ("razon_social",)
