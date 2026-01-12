from django.db import models
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.conf import settings
from clientes.models import Cliente
from core.choices import (
    ESTATUS_PROCESO_CHOICES,
    ESTATUS_PERIODO_CHOICES,
    ESTATUS_PAGO_CHOICES,
    FACTURADORA_CHOICES,
)

class Dispersion(models.Model):
    fecha = models.DateField(default=timezone.localdate)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    ejecutivo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dispersiones_ejecutivo",
    )
    ejecutivo2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dispersiones_ejecutivo2",
    )
    ejecutivo_apoyo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dispersiones_apoyo",
    )
    servicio = models.CharField(max_length=50)
    facturadora = models.CharField(max_length=100, blank=True, null=True, choices=FACTURADORA_CHOICES)
    num_factura = models.CharField(max_length=100, blank=True, null=True)
    monto_dispersion = models.DecimalField(max_digits=12, decimal_places=2)
    comision_porcentaje = models.DecimalField(max_digits=7, decimal_places=4, editable=False)
    monto_comision = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    monto_comision_iva = models.DecimalField(max_digits=12, decimal_places=2, editable=False, null=True, blank=True)
    num_factura_honorarios = models.CharField(max_length=100, blank=True, null=True)
    estatus_proceso = models.CharField(max_length=20, choices=ESTATUS_PROCESO_CHOICES, default="Pendiente")
    comentarios = models.CharField(max_length=255, blank=True, null=True)
    num_periodo = models.CharField(max_length=50, blank=True, null=True)
    estatus_periodo = models.CharField(max_length=20, choices=ESTATUS_PERIODO_CHOICES, default="Pendiente")
    estatus_pago = models.CharField(max_length=20, choices=ESTATUS_PAGO_CHOICES, default="Pendiente")

    def __str__(self):
        return f"{self.cliente} - {self.facturadora} - {self.fecha}"

    def save(self, *args, **kwargs):
        if not self.ejecutivo_id and getattr(self, "cliente_id", None):
            self.ejecutivo = getattr(self.cliente, "ejecutivo", None)
        if not self.ejecutivo2_id and getattr(self, "cliente_id", None):
            self.ejecutivo2 = getattr(self.cliente, "ejecutivo2", None)
        if not self.ejecutivo_apoyo_id and getattr(self, "cliente_id", None):
            self.ejecutivo_apoyo = getattr(self.cliente, "ejecutivo_apoyo", None)
        rate = None
        try:
            # Preferimos comision_servicio (fracción 0..1) si existe en el cliente
            if getattr(self.cliente, "comision_servicio", None) is not None:
                rate = Decimal(str(self.cliente.comision_servicio))
            elif getattr(self.cliente, "comision_procom", None) is not None:
                rate = Decimal(str(self.cliente.comision_procom))
        except (InvalidOperation, TypeError):
            rate = None

        if rate is None:
            rate_fraction = Decimal("0")
            rate_percent = Decimal("0")
        else:
            rate_fraction = rate if rate <= 1 else (rate / Decimal("100"))
            rate_percent = rate * Decimal("100") if rate <= 1 else rate
        # Regla CONFEDIN: restar 0.2 puntos porcentuales antes de calcular comision
        try:
            if getattr(self.cliente, "ac", None) == "CONFEDIN":
                rate_fraction = max(Decimal("0"), rate_fraction - Decimal("0.002"))
                rate_percent = max(Decimal("0"), rate_percent - Decimal("0.2"))
        except Exception:
            pass

        # Copiar servicio legible del cliente
        try:
            self.servicio = self.cliente.get_servicio_display()
        except Exception:
            try:
                self.servicio = str(self.cliente.servicio)
            except Exception:
                pass

        # Calcular montos
        if self.monto_dispersion is None:
            self.monto_dispersion = Decimal("0")
        self.comision_porcentaje = rate_percent.quantize(Decimal("0.0001"))
        self.monto_comision = (rate_fraction * self.monto_dispersion).quantize(Decimal("0.01"))
        self.monto_comision_iva = (self.monto_comision * Decimal("1.16")).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
