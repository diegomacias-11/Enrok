from calendar import monthrange
from decimal import Decimal
from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model
from clientes.models import Cliente
from .models import Dispersion


def _is_ejecutivo_restringido(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return (
        user.groups.filter(name__iexact="Ejecutivo Jr").exists()
        or user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or user.groups.filter(name__iexact="Ejecutivo Apoyo").exists()
    )


class ClienteSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        obj = getattr(value, "instance", None)
        if not obj:
            return option
        try:
            ac = obj.get_ac_display()
        except Exception:
            ac = ""
        try:
            servicio = obj.get_servicio_display()
        except Exception:
            servicio = str(getattr(obj, "servicio", ""))
        comision = ""
        try:
            pct = obj.comision_servicio or Decimal("0")
            comision = f"{(Decimal(pct) * Decimal('100')).quantize(Decimal('0.01'))}%"
        except Exception:
            comision = ""
        ejecutivo_id = getattr(obj, "ejecutivo_id", "") or ""
        ejecutivo2_id = getattr(obj, "ejecutivo2_id", "") or ""
        apoyo_id = ""
        try:
            apoyo = obj.ejecutivos_apoyo.first()
            apoyo_id = getattr(apoyo, "id", "") or ""
        except Exception:
            apoyo_id = ""
        option["attrs"].update(
            {
                "data-ac": ac,
                "data-servicio": servicio,
                "data-comision": comision,
                "data-ejecutivo-id": str(ejecutivo_id),
                "data-ejecutivo2-id": str(ejecutivo2_id),
                "data-apoyo-id": str(apoyo_id),
            }
        )
        return option


class DispersionForm(forms.ModelForm):
    monto_comision_iva = forms.DecimalField(required=False, disabled=True)

    class Meta:
        model = Dispersion
        fields = [
            "fecha",
            "cliente",
            "ejecutivo",
            "ejecutivo2",
            "ejecutivo_apoyo",
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
            "cliente": ClienteSelect(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.mes = kwargs.pop("mes", None)
        self.anio = kwargs.pop("anio", None)
        super().__init__(*args, **kwargs)

        self._is_ejecutivo = _is_ejecutivo_restringido(self.user)
        self.cliente_info = None
        User = get_user_model()

        if "cliente" in self.fields and self.user and self.user.is_superuser:
            self.fields["cliente"].queryset = Cliente.objects.all()
        elif "cliente" in self.fields and self._is_ejecutivo:
            allowed = Cliente.objects.filter(
                Q(ejecutivo=self.user) | Q(ejecutivo2=self.user) | Q(ejecutivos_apoyo=self.user)
            ).distinct()
            self.fields["cliente"].queryset = allowed

        if "cliente" in self.fields:
            self.fields["cliente"].label_from_instance = (
                lambda obj: f"{getattr(obj, 'razon_social', '')} - "
                            f"{getattr(obj, 'get_servicio_display', lambda: getattr(obj, 'servicio', ''))()}"
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
                "ejecutivo2": getattr(cliente_obj, "ejecutivo2", None),
                "apoyos": list(cliente_obj.ejecutivos_apoyo.all()) if hasattr(cliente_obj, "ejecutivos_apoyo") else [],
                "comision_servicio": pct_display,
            }

        for field_name in ("ejecutivo", "ejecutivo2", "ejecutivo_apoyo"):
            if field_name in self.fields:
                self.fields[field_name].queryset = User.objects.all().order_by("username")
                self.fields[field_name].label_from_instance = (
                    lambda u: f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
                    or getattr(u, "username", "")
                )
                self.fields[field_name].disabled = True
                self.fields[field_name].required = False
                if not self.instance.pk and cliente_obj:
                    if field_name == "ejecutivo":
                        self.initial[field_name] = getattr(cliente_obj, "ejecutivo_id", None)
                    elif field_name == "ejecutivo2":
                        self.initial[field_name] = getattr(cliente_obj, "ejecutivo2_id", None)
                    elif field_name == "ejecutivo_apoyo":
                        try:
                            apoyo = cliente_obj.ejecutivos_apoyo.first()
                        except Exception:
                            apoyo = None
                        self.initial[field_name] = getattr(apoyo, "id", None)

        if self.instance and getattr(self.instance, "pk", None):
            for fname in ("cliente", "monto_dispersion"):
                if fname in self.fields:
                    self.fields[fname].disabled = True
                    self.fields[fname].required = False
            if self.instance.fecha is not None:
                self.initial["fecha"] = self.instance.fecha.isoformat()
        if "monto_comision_iva" in self.fields and self.instance:
            self.initial["monto_comision_iva"] = getattr(self.instance, "monto_comision_iva", None)

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
                cleaned["estatus_pago"] = self.fields["estatus_pago"].initial or "Pendiente"
        return cleaned
