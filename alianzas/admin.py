from django.contrib import admin

from .models import Alianza


@admin.register(Alianza)
class AlianzaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo_electronico")
    search_fields = ("nombre", "correo_electronico")
