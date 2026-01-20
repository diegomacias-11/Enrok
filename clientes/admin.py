from django.contrib import admin
from .models import Cliente


@admin.action(description="Re-guardar clientes seleccionados")
def resave_clientes(modeladmin, request, queryset):
    total = queryset.count()
    for c in queryset.iterator():
        c.save()
    modeladmin.message_user(request, f"Re-guardados {total} clientes.")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "servicio", "ejecutivo", "fecha_registro")
    search_fields = ("razon_social",)
    actions = [resave_clientes]
