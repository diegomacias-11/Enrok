from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.db.models import Q
from django.contrib.auth import get_user_model, models as auth_models
from .models import Cliente

PERCENT_Q = Decimal("0.000001")


def _percent_to_fraction(val):
    return (Decimal(val) / Decimal("100")).quantize(PERCENT_Q)


User = get_user_model()


def _label_user(u):
    name = f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
    return name or getattr(u, "username", "")


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "razon_social",
            "ac",
            "ejecutivo",
            "ejecutivos_apoyo",
            "servicio",
            "comision_servicio",
            *[f"comisionista{i}" for i in range(1, 13)],
            *[f"comision{i}" for i in range(1, 13)],
        ]
        widgets = {
            **{f"comision{i}": forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}) for i in range(1, 13)},
            "comision_servicio": forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
            "ejecutivos_apoyo": forms.Select(),
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
            self.fields["ejecutivo"].label_from_instance = _label_user
            self.fields["ejecutivo"].required = False
            if "ejecutivos_apoyo" in self.fields:
                principal_id = None
                if self.is_bound:
                    principal_id = self.data.get("ejecutivo") or self.initial.get("ejecutivo")
                elif self.instance and getattr(self.instance, "ejecutivo_id", None):
                    principal_id = self.instance.ejecutivo_id
                apoyo_qs = qset.exclude(id=principal_id) if principal_id else qset
                self.fields["ejecutivos_apoyo"] = forms.ModelChoiceField(
                    queryset=apoyo_qs.order_by("username"),
                    required=False,
                    empty_label="---------",
                    widget=forms.Select(),
                    label=self.fields["ejecutivos_apoyo"].label,
                )
                self.fields["ejecutivos_apoyo"].label_from_instance = _label_user
        if "comision_servicio" in self.fields:
            self.fields["comision_servicio"].required = False
            self.fields["comision_servicio"].disabled = True
        if self.instance and getattr(self.instance, "pk", None) and not self.is_bound:
            for i in range(1, 13):
                key = f"comision{i}"
                val = getattr(self.instance, key, None)
                if val is not None:
                    percent = (Decimal(val) * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    self.initial[key] = format(percent, 'f')
            total = Decimal("0")
            for i in range(1, 13):
                val = getattr(self.instance, f"comision{i}", None)
                if val is not None:
                    total += Decimal(val)
            percent = (total * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            self.initial["comision_servicio"] = format(percent, 'f')
        elif self.is_bound:
            total = Decimal("0")
            for i in range(1, 13):
                val = self.data.get(f"comision{i}")
                if val in (None, ""):
                    continue
                try:
                    total += _percent_to_fraction(val)
                except Exception:
                    continue
            percent = (total * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            self.initial["comision_servicio"] = format(percent, 'f')
        for i in range(1, 13):
            f = f"comision{i}"
            if f in self.fields:
                self.fields[f].widget.attrs["step"] = "any"
                self.fields[f].widget.attrs["inputmode"] = "decimal"
        self.fields["comision_servicio"].widget.attrs["step"] = "any"
        self.fields["comision_servicio"].widget.attrs["inputmode"] = "decimal"

    def clean(self):
        cleaned = super().clean()
        exec_obj = cleaned.get("ejecutivo")
        exec_id = exec_obj.id if exec_obj else None
        apoyo = cleaned.get("ejecutivos_apoyo")
        if exec_id and apoyo and getattr(apoyo, "id", None) == exec_id:
            self.add_error("ejecutivos_apoyo", "No puedes seleccionar al ejecutivo principal como apoyo.")

        total_comisionistas = Decimal("0")
        for i in range(1, 13):
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
        cleaned["comision_servicio"] = total_comisionistas
        return cleaned

    def save(self, commit=True):
        apoyo = self.cleaned_data.get("ejecutivos_apoyo")
        obj = super().save(commit=False)
        if commit:
            obj.save()
            if apoyo:
                obj.ejecutivos_apoyo.set([apoyo])
            else:
                obj.ejecutivos_apoyo.clear()
        else:
            self._pending_apoyo = apoyo
        return obj

    def save_m2m(self):
        super().save_m2m()
        apoyo = getattr(self, "_pending_apoyo", None)
        if apoyo is not None:
            if apoyo:
                self.instance.ejecutivos_apoyo.set([apoyo])
            else:
                self.instance.ejecutivos_apoyo.clear()
