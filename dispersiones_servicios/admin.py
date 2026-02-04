from django.contrib import admin

from .models import Dispersion


@admin.action(description="Re-guardar dispersiones seleccionadas")
def resave_dispersiones(modeladmin, request, queryset):
    total = queryset.count()
    for d in queryset.iterator():
        d.save()
    modeladmin.message_user(request, f"Re-guardadas {total} dispersiones.")


@admin.register(Dispersion)
class DispersionAdmin(admin.ModelAdmin):
    actions = [resave_dispersiones]
