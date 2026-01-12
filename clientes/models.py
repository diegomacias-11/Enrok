from decimal import Decimal
from django.conf import settings
from django.db import models
from alianzas.models import Alianza
from core.choices import AC_CHOICES, SERVICIO_CHOICES


class Cliente(models.Model):
    razon_social = models.CharField(max_length=200)
    ejecutivo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clientes_ejecutivo",
    )
    ejecutivo2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clientes_ejecutivo2",
    )
    ejecutivo_apoyo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clientes_apoyo",
    )
    ac = models.CharField(max_length=20, choices=AC_CHOICES, null=True, blank=True)
    servicio = models.CharField(max_length=50, choices=SERVICIO_CHOICES)
    # Comision global por servicio (0..1 almacenado)
    # Permite alta precision (hasta 6 decimales tras convertir a fraccion)
    comision_servicio = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # 12 pares de comisionista / comision (porcentaje en 0..1)
    comisionista1 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista1")
    comision1 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista2 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista2")
    comision2 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista3 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista3")
    comision3 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista4 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista4")
    comision4 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista5 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista5")
    comision5 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista6 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista6")
    comision6 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista7 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista7")
    comision7 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista8 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista8")
    comision8 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista9 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista9")
    comision9 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista10 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista10")
    comision10 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista11 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista11")
    comision11 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    comisionista12 = models.ForeignKey(Alianza, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes_comisionista12")
    comision12 = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        try:
            servicio = self.get_servicio_display()
        except Exception:
            servicio = str(self.servicio)
        return f"{self.razon_social} - {servicio}"

    def save(self, *args, **kwargs):
        if self.razon_social is not None:
            self.razon_social = self.razon_social.strip().upper()
        total_comision = Decimal("0")
        for i in range(1, 13):
            val = getattr(self, f"comision{i}", None)
            if val is not None:
                total_comision += val
        self.comision_servicio = total_comision
        super().save(*args, **kwargs)
