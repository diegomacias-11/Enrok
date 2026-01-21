from calendar import monthrange
from decimal import Decimal
from django import forms
from django.db.models import Q
from django.utils import timezone
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
    )

def _is_apoyo(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return user.groups.filter(name__iexact="Ejecutivo Apoyo").exists()


def _can_edit_estatus_pago(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return (
        user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or user.groups.filter(name__iexact="Direccion Operaciones").exists()
    )



def _is_contabilidad(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return user.groups.filter(name__iexact="Contabilidad").exists()


def _can_ver_todos_clientes(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return (
        user.groups.filter(name__iexact="Ejecutivo Sr").exists()
        or user.groups.filter(name__iexact="Direccion Operaciones").exists()
        or user.groups.filter(name__iexact="Dirección Operaciones").exists()
    )


def _format_comision_display(cliente):
    try:
        pct_fraction = Decimal(str(cliente.comision_servicio or "0"))
    except Exception:
        return ""
    rate_percent = (pct_fraction * Decimal("100"))
    try:
        if getattr(cliente, "ac", None) == "CONFEDIN":
            rate_percent = max(Decimal("0"), rate_percent - Decimal("0.2"))
    except Exception:
        pass
    return f"{rate_percent.quantize(Decimal('0.01'))}%"


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
        comision = _format_comision_display(obj)
        ejecutivo_id = getattr(obj, "ejecutivo_id", "") or ""
        try:
            forma_pago = obj.get_forma_pago_display()
        except Exception:
            forma_pago = getattr(obj, "forma_pago", "") or ""
        option["attrs"].update(
            {
                "data-ac": ac,
                "data-servicio": servicio,
                "data-comision": comision,
                "data-facturadora": getattr(obj, "facturadora", "") or "",
                "data-forma-pago": forma_pago,
                "data-ejecutivo-id": str(ejecutivo_id),
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
            "num_factura",
            "monto_dispersion",
            "num_factura_honorarios",
            "estatus_proceso",
            "num_periodo",
            "estatus_periodo",
            "comentarios",
            "estatus_pago",
            "factura_solicitada",
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
        self._is_apoyo = _is_apoyo(self.user)
        self._is_contabilidad = _is_contabilidad(self.user)
        self.cliente_info = None
        User = get_user_model()

        if "cliente" in self.fields and self.user and self.user.is_superuser:
            self.fields["cliente"].queryset = Cliente.objects.all().order_by("razon_social")
        elif "cliente" in self.fields and self._is_ejecutivo:
            if _can_ver_todos_clientes(self.user):
                self.fields["cliente"].queryset = Cliente.objects.all().order_by("razon_social")
            else:
                allowed = Cliente.objects.filter(
                    Q(ejecutivo=self.user) | Q(ejecutivo2=self.user) | Q(ejecutivo_apoyo=self.user)
                ).distinct()
                self.fields["cliente"].queryset = allowed.order_by("razon_social")

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
            self.cliente_info = {
                "razon_social": cliente_obj.razon_social,
                "ac": cliente_obj.get_ac_display() if hasattr(cliente_obj, "get_ac_display") else "",
                "servicio": getattr(cliente_obj, "get_servicio_display", lambda: getattr(cliente_obj, "servicio", ""))(),
                "comision_servicio": _format_comision_display(cliente_obj),
                "facturadora": getattr(cliente_obj, "facturadora", "") or "",
                "forma_pago": cliente_obj.get_forma_pago_display() if hasattr(cliente_obj, "get_forma_pago_display") else "",
            }

        for field_name in ("ejecutivo",):
            if field_name in self.fields:
                self.fields[field_name].queryset = User.objects.all().order_by("username")
                self.fields[field_name].label_from_instance = (
                    lambda u: f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
                    or getattr(u, "username", "")
                )
                self.fields[field_name].disabled = True
                self.fields[field_name].required = False
                if self.instance and getattr(self.instance, "pk", None):
                    self.initial[field_name] = getattr(self.instance, f"{field_name}_id", None)
                elif self.user and getattr(self.user, "is_authenticated", False):
                    self.initial[field_name] = getattr(self.user, "id", None)

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
                today = timezone.localdate()
                if today.month == int(self.mes) and today.year == int(self.anio):
                    self.initial["fecha"] = today.isoformat()
                else:
                    self.initial["fecha"] = first_day

        if self._is_ejecutivo and "estatus_pago" in self.fields and not _can_edit_estatus_pago(self.user):
            self.fields["estatus_pago"].disabled = True
            if self.instance and getattr(self.instance, "pk", None):
                self.initial["estatus_pago"] = self.instance.estatus_pago

        if self._is_contabilidad:
            for name, field in self.fields.items():
                if name != "num_factura_honorarios":
                    field.disabled = True
                    field.required = False
        elif "num_factura_honorarios" in self.fields and not getattr(self.user, "is_superuser", False):
            self.fields["num_factura_honorarios"].disabled = True
            self.fields["num_factura_honorarios"].required = False
        if self._is_apoyo:
            allowed = {"estatus_proceso", "estatus_periodo"}
            for name, field in self.fields.items():
                if name not in allowed:
                    field.disabled = True
                    field.required = False

    def clean_fecha(self):
        fecha = self.cleaned_data.get("fecha")
        if fecha and self.mes and self.anio:
            if fecha.month != int(self.mes) or fecha.year != int(self.anio):
                raise forms.ValidationError("La fecha debe pertenecer al mes filtrado.")
        return fecha

    def clean(self):
        cleaned = super().clean()
        if self._is_ejecutivo and not _can_edit_estatus_pago(self.user):
            if self.instance and getattr(self.instance, "pk", None):
                cleaned["estatus_pago"] = self.instance.estatus_pago
            else:
                cleaned["estatus_pago"] = self.fields["estatus_pago"].initial or "Pendiente"
        if self._is_apoyo and self.instance and getattr(self.instance, "pk", None):
            allowed = {"estatus_proceso", "estatus_periodo"}
            for name in self.fields.keys():
                if name not in allowed:
                    cleaned[name] = getattr(self.instance, name)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not getattr(obj, "ejecutivo_id", None) and self.user and getattr(self.user, "is_authenticated", False):
            obj.ejecutivo = self.user
        if commit:
            obj.save()
        return obj
