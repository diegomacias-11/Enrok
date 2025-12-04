from django.conf import settings
from django.db import models
from alianzas.models import Alianza


class Cliente(models.Model):
    class Servicio(models.TextChoices):
        PROCOM = "PROCOM", "PROCOM"
        MUTUALINK = "MUTUALINK", "Mutualink"
        PRESTAMO = "PRESTAMO", "Prestamo"
        PRAIDS = "PRAIDS", "PRAIDS"
        MONEDEROS = "MONEDEROS", "Monederos"
        HIDROCARBUROS = "HIDROCARBUROS", "Hidrocarburos"
        VP360 = "VP360", "VP360"

    razon_social = models.CharField(max_length=200)
    ejecutivo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clientes_ejecutivo",
    )
    ejecutivos_apoyo = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="clientes_apoyo",
    )
    class AC(models.TextChoices):
        CONFEDIN = "CONFEDIN", "CONFEDIN"
        CAMARENCE = "CAMARENCE", "CAMARENCE"
        SERVIARUGA = "SERVIARUGA", "SERVIARUGA"
        ZAMORA = "ZAMORA", "ZAMORA"
        INACTIVO = "INACTIVO", "INACTIVO"

    ac = models.CharField(max_length=20, choices=AC.choices, default=AC.CONFEDIN)
    servicio = models.CharField(max_length=20, choices=Servicio.choices)
    # Comision global por servicio (0..1 almacenado)
    # Permite alta precision (hasta 6 decimales tras convertir a fraccion)
    comision_servicio = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # 10 pares de comisionista / comision (porcentaje en 0..1)
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

    def __str__(self):
        try:
            servicio = self.get_servicio_display()
        except Exception:
            servicio = str(self.servicio)
        return f"{self.razon_social} - {servicio}"

    def save(self, *args, **kwargs):
        if self.razon_social is not None:
            self.razon_social = self.razon_social.strip().upper()
        super().save(*args, **kwargs)
