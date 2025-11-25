from django.db import models
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from clientes.models import Cliente

class Dispersion(models.Model):
    class EstatusProceso(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        ENVIADA = "Enviada", "Enviada"
        APLICADA = "Aplicada", "Aplicada"

    class EstatusPeriodo(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        CERRADO = "Cerrado", "Cerrado"
        TIMBRADO = "Timbrado", "Timbrado"
        ENVIADO = "Enviado", "Enviado"
        ENVIADO_IND = "Enviado ind.", "Enviado ind."
        DRIVE = "Drive", "Drive"

    class EstatusPago(models.TextChoices):
        PENDIENTE = "Pendiente", "Pendiente"
        PAGADO = "Pagado", "Pagado"

    fecha = models.DateField(default=timezone.localdate)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    servicio = models.CharField(max_length=50)
    facturadora = models.CharField(max_length=100,blank=True, null=True)
    num_factura = models.CharField(max_length=100, blank=True, null=True)
    monto_dispersion = models.DecimalField(max_digits=12, decimal_places=2)
    comision_porcentaje = models.DecimalField(max_digits=7, decimal_places=4, editable=False)
    monto_comision = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    num_factura_honorarios = models.CharField(max_length=100, blank=True, null=True)
    estatus_proceso = models.CharField(max_length=20, choices=EstatusProceso.choices, default=EstatusProceso.PENDIENTE)
    comentarios = models.CharField(max_length=255, blank=True, null=True)
    num_periodo = models.CharField(max_length=50, blank=True, null=True)
    estatus_periodo = models.CharField(max_length=20, choices=EstatusPeriodo.choices, default=EstatusPeriodo.PENDIENTE)
    estatus_pago = models.CharField(max_length=20, choices=EstatusPago.choices, default=EstatusPago.PENDIENTE)

    def __str__(self):
        return f"{self.cliente} - {self.facturadora} - {self.fecha}"

    def save(self, *args, **kwargs):
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
        super().save(*args, **kwargs)
