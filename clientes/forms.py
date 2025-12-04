from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model, models as auth_models
from .models import Cliente

PERCENT_Q = Decimal("0.000001")

def _percent_to_fraction(val):
    return (Decimal(val) / Decimal("100")).quantize(PERCENT_Q)


User = get_user_model()


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "razon_social",
            "ejecutivo",
            "ejecutivos_apoyo",
            "servicio",
            "comision_servicio",
            # pares 1..10
            *[f"comisionista{i}" for i in range(1, 11)],
            *[f"comision{i}" for i in range(1, 11)],
        ]
        widgets = {
            **{f"comision{i}": forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}) for i in range(1, 11)},
            "comision_servicio": forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
            "ejecutivos_apoyo": forms.SelectMultiple(attrs={"size": "6"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "ejecutivo" in self.fields:
            try:
                grupo = auth_models.Group.objects.get(name__iexact="Ejecutivo")
                qset = grupo.user_set.all()
            except auth_models.Group.DoesNotExist:
                qset = User.objects.none()
            self.fields["ejecutivo"].queryset = qset.order_by("username")
            self.fields["ejecutivo"].required = False
            if "ejecutivos_apoyo" in self.fields:
                self.fields["ejecutivos_apoyo"].queryset = qset.order_by("username")
                self.fields["ejecutivos_apoyo"].required = False
        # Hacer obligatorio comision_servicio
        if 'comision_servicio' in self.fields:
            self.fields['comision_servicio'].required = True
        # Mostrar porcentajes como enteros al editar
        if self.instance and getattr(self.instance, "pk", None) and not self.is_bound:
            for i in range(1, 11):
                key = f"comision{i}"
                val = getattr(self.instance, key, None)
                if val is not None:
                    # Mostrar con hasta 6 decimales (sin notaci?n cient?fica)
                    percent = (Decimal(val) * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    self.initial[key] = format(percent, 'f')
            # comision por servicio
            val = getattr(self.instance, "comision_servicio", None)
            if val is not None:
                percent = (Decimal(val) * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                self.initial["comision_servicio"] = format(percent, 'f')
        # Asegurar step=1 e inputmode numeric
        for i in range(1, 11):
            f = f"comision{i}"
            if f in self.fields:
                self.fields[f].widget.attrs["step"] = "any"
                self.fields[f].widget.attrs["inputmode"] = "decimal"
        self.fields["comision_servicio"].widget.attrs["step"] = "any"
        self.fields["comision_servicio"].widget.attrs["inputmode"] = "decimal"

    def clean(self):
        cleaned = super().clean()
        # comision por servicio
        val_cs = cleaned.get("comision_servicio")
        if val_cs in (None, ""):
            self.add_error("comision_servicio", "Este campo es obligatorio.")
        else:
            try:
                cleaned["comision_servicio"] = _percent_to_fraction(val_cs)
            except Exception:
                self.add_error("comision_servicio", "Valor inv?lido.")
        total_comisionistas = Decimal("0")
        for i in range(1, 11):
            key = f"comision{i}"
            val = cleaned.get(key)
            if val in (None, ""):
                continue
            try:
                dec = _percent_to_fraction(val)
            except Exception:
                continue
            cleaned[key] = dec
            total_comisionistas += dec
        # Validar que la suma de comisionistas no exceda ni sea menor a la comisi?n del servicio
        cs = cleaned.get("comision_servicio")
        if cs not in (None, ""):
            try:
                eps = PERCENT_Q
                if total_comisionistas > cs + eps:
                    self.add_error(None, "La suma de porcentajes de comisionistas supera la comisi?n por servicio.")
                elif total_comisionistas + eps < cs:
                    self.add_error(None, "La suma de porcentajes de comisionistas es menor que la comisi?n por servicio.")
            except Exception:
                pass
        return cleaned
