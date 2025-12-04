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
    def save(self, commit=True):
        # Manejar que ejecutivos_apoyo viene como ModelChoiceField (un solo apoyo opcional)
        apoyo = self.cleaned_data.get("ejecutivos_apoyo")
        obj = super().save(commit=False)
        if commit:
            obj.save()
            # Asignar apoyo único si existe, o limpiar
            if apoyo:
                obj.ejecutivos_apoyo.set([apoyo])
            else:
                obj.ejecutivos_apoyo.clear()
        else:
            # Si no se hace commit, posponer asignación de M2M
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
    class Meta:
        model = Cliente
        fields = [
            "razon_social",
            "ac",
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
            self.fields["ejecutivo"].label_from_instance = (
                lambda u: f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip() or getattr(u, "username", "")
            )
            self.fields["ejecutivo"].required = False
            if "ejecutivos_apoyo" in self.fields:
                # Excluir al ejecutivo principal de la lista de apoyo
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
                )
                self.fields["ejecutivos_apoyo"].label_from_instance = (
                    lambda u: f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip() or getattr(u, "username", "")
                )
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
        # Validar que el principal no esté en apoyos
        exec_id = cleaned.get("ejecutivo").id if cleaned.get("ejecutivo") else None
        apoyos = cleaned.get("ejecutivos_apoyo") or []
        if exec_id and any(getattr(a, "id", None) == exec_id for a in apoyos):
            self.add_error("ejecutivos_apoyo", "No puedes seleccionar al ejecutivo principal como apoyo.")
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
