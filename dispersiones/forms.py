from django import forms
from calendar import monthrange
from .models import Dispersion
from clientes.models import Cliente
from django.db.models import Q


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
        # Restringir clientes según asignación si es Ejecutivo
        if "cliente" in self.fields and self._is_ejecutivo:
            allowed = Cliente.objects.filter(
                Q(ejecutivo=self.user) | Q(ejecutivos_apoyo=self.user)
            ).distinct()
            self.fields["cliente"].queryset = allowed

        # Mostrar cliente como RAZÓN SOCIAL – SERVICIO para diferenciar homónimos
        if 'cliente' in self.fields:
            self.fields['cliente'].label_from_instance = (
                lambda obj: f"{getattr(obj, 'razon_social', '')} – "
                            f"{getattr(obj, 'get_servicio_display', lambda: getattr(obj,'servicio',''))()}"
            )

        # En edición: no permitir cambiar cliente ni monto de dispersión
        if self.instance and getattr(self.instance, "pk", None):
            for fname in ("cliente", "monto_dispersion"):
                if fname in self.fields:
                    self.fields[fname].disabled = True
                    self.fields[fname].required = False
            # Asegurar que la fecha se muestre con el día registrado
            if self.instance.fecha is not None:
                # isoformat() -> YYYY-MM-DD, compatible con type=date
                self.initial["fecha"] = self.instance.fecha.isoformat()

        # Restringir fecha al mes/año del filtro
        if self.mes and self.anio:
            first_day = f"{int(self.anio):04d}-{int(self.mes):02d}-01"
            last_dom = monthrange(int(self.anio), int(self.mes))[1]
            last_day = f"{int(self.anio):04d}-{int(self.mes):02d}-{last_dom:02d}"
            self.fields["fecha"].widget.attrs.update({"min": first_day, "max": last_day})
            if not self.initial.get("fecha") and not (self.instance and self.instance.pk):
                self.initial["fecha"] = first_day

        # Ejecutivos no pueden modificar estatus_pago
        if self._is_ejecutivo and "estatus_pago" in self.fields:
            self.fields["estatus_pago"].disabled = True
            # Mostrar el valor actual
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
            # Forzar estatus_pago al valor existente para evitar cambios por POST
            if self.instance and getattr(self.instance, "pk", None):
                cleaned["estatus_pago"] = self.instance.estatus_pago
            else:
                cleaned["estatus_pago"] = self.fields["estatus_pago"].initial or Dispersion.EstatusPago.PENDIENTE
        return cleaned
