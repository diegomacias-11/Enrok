from calendar import monthrange
from decimal import Decimal
from django import forms
from django.db.models import Q
from clientes.models import Cliente
from .models import Dispersion
from core.choices import ESTATUS_PAGO_PENDIENTE


class DispersionForm(forms.ModelForm):
    class Meta:
        model = Dispersion
        fields = [
            "fecha",
            "cliente",
            "facturadora",
            "num_factura",
            "monto_dispersion",
            "num_factura_honorarios",
            "estatus_proceso",
            "num_periodo",
            "estatus_periodo",
            "comentarios",
            "estatus_pago",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.mes = kwargs.pop("mes", None)
        self.anio = kwargs.pop("anio", None)
        super().__init__(*args, **kwargs)

        self._is_ejecutivo = False
        if self.user and hasattr(self.user, "groups"):
            self._is_ejecutivo = self.user.groups.filter(name__iexact="Ejecutivo").exists()
        self.cliente_info = None

        if "cliente" in self.fields and self._is_ejecutivo:
            allowed = Cliente.objects.filter(
                Q(ejecutivo=self.user) | Q(ejecutivos_apoyo=self.user)
            ).distinct()
            self.fields["cliente"].queryset = allowed

        if "cliente" in self.fields:
            self.fields["cliente"].label_from_instance = (
                lambda obj: f"{getattr(obj, 'razon_social', '')} – "
                            f"{getattr(obj, 'get_servicio_display', lambda: getattr(obj,'servicio',''))()}"
            )

        cliente_obj = None
        if self.instance and getattr(self.instance, "cliente_id", None):
            cliente_obj = self.instance.cliente
        elif self.is_bound:
            try:
                cliente_id = self.data.get("cliente") or self.initial.get("cliente")
                if cliente_id:
                    cliente_obj = Cliente.objects.filter(id=cliente_id).first()
            except Exception:
                cliente_obj = None
        if cliente_obj:
            pct = cliente_obj.comision_servicio or Decimal("0")
            pct_display = f"{(Decimal(pct) * Decimal('100')).quantize(Decimal('0.01'))}%" if pct is not None else ""
            self.cliente_info = {
                "razon_social": cliente_obj.razon_social,
                "ac": cliente_obj.get_ac_display() if hasattr(cliente_obj, "get_ac_display") else "",
                "servicio": getattr(cliente_obj, "get_servicio_display", lambda: getattr(cliente_obj, "servicio", ""))(),
                "ejecutivo": getattr(cliente_obj, "ejecutivo", None),
                "apoyos": list(cliente_obj.ejecutivos_apoyo.all()) if hasattr(cliente_obj, "ejecutivos_apoyo") else [],
                "comision_servicio": pct_display,
            }

        if self.instance and getattr(self.instance, "pk", None):
            for fname in ("cliente", "monto_dispersion"):
                if fname in self.fields:
                    self.fields[fname].disabled = True
                    self.fields[fname].required = False
            if self.instance.fecha is not None:
                self.initial["fecha"] = self.instance.fecha.isoformat()

        if self.mes and self.anio:
            first_day = f"{int(self.anio):04d}-{int(self.mes):02d}-01"
            last_dom = monthrange(int(self.anio), int(self.mes))[1]
            last_day = f"{int(self.anio):04d}-{int(self.mes):02d}-{last_dom:02d}"
            self.fields["fecha"].widget.attrs.update({"min": first_day, "max": last_day})
            if not self.initial.get("fecha") and not (self.instance and self.instance.pk):
                self.initial["fecha"] = first_day

        if self._is_ejecutivo and "estatus_pago" in self.fields:
            self.fields["estatus_pago"].disabled = True
            if self.instance and getattr(self.instance, "pk", None):
                self.initial["estatus_pago"] = self.instance.estatus_pago

    def clean_fecha(self):
        fecha = self.cleaned_data.get("fecha")
        if fecha and self.mes and self.anio:
            if fecha.month != int(self.mes) or fecha.year != int(self.anio):
                raise forms.ValidationError("La fecha debe pertenecer al mes filtrado.")
        return fecha

    def clean(self):
        cleaned = super().clean()
        if self._is_ejecutivo:
            if self.instance and getattr(self.instance, "pk", None):
                cleaned["estatus_pago"] = self.instance.estatus_pago
            else:
                cleaned["estatus_pago"] = self.fields["estatus_pago"].initial or ESTATUS_PAGO_PENDIENTE
        return cleaned
