from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.contrib.auth import get_user_model, models as auth_models
from .models import Cliente

PERCENT_Q = Decimal("0.000001")


def _percent_to_fraction(val):
    return (Decimal(val) / Decimal("100")).quantize(PERCENT_Q)


User = get_user_model()


def _label_user(u):
    name = f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}".strip()
    return name or getattr(u, "username", "")


def _users_in_group(name: str):
    try:
        grupo = auth_models.Group.objects.get(name__iexact=name)
    except auth_models.Group.DoesNotExist:
        return User.objects.none()
    return grupo.user_set.all()


def _user_in_groups(user, names):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return False
    return any(user.groups.filter(name__iexact=name).exists() for name in names)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "razon_social",
            "ac",
            "ejecutivo",
            "ejecutivo2",
            "ejecutivo_apoyo",
            "servicio",
            "comision_servicio",
            *[f"comisionista{i}" for i in range(1, 13)],
            *[f"comision{i}" for i in range(1, 13)],
        ]
        widgets = {
            **{f"comision{i}": forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}) for i in range(1, 13)},
            "comision_servicio": forms.NumberInput(attrs={"step": "any", "inputmode": "decimal"}),
            "ejecutivo_apoyo": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if "ac" in self.fields:
            self.fields["ac"].empty_label = "---------"

        jr_qs = _users_in_group("Ejecutivo Jr")
        apoyo_qs = _users_in_group("Ejecutivo Apoyo")

        exec1_id = None
        exec2_id = None
        if self.is_bound:
            exec1_id = self.data.get("ejecutivo") or self.initial.get("ejecutivo")
            exec2_id = self.data.get("ejecutivo2") or self.initial.get("ejecutivo2")
        elif self.instance and getattr(self.instance, "pk", None):
            exec1_id = self.instance.ejecutivo_id
            exec2_id = self.instance.ejecutivo2_id

        if "ejecutivo" in self.fields:
            exec1_qs = jr_qs.exclude(id=exec2_id) if exec2_id else jr_qs
            self.fields["ejecutivo"].queryset = exec1_qs.order_by("username")
            self.fields["ejecutivo"].label_from_instance = _label_user
            self.fields["ejecutivo"].required = False

        if "ejecutivo2" in self.fields:
            exec2_qs = jr_qs.exclude(id=exec1_id) if exec1_id else jr_qs
            self.fields["ejecutivo2"].queryset = exec2_qs.order_by("username")
            self.fields["ejecutivo2"].label_from_instance = _label_user
            self.fields["ejecutivo2"].required = False

        if "ejecutivo_apoyo" in self.fields:
            exclude_ids = [i for i in (exec1_id, exec2_id) if i]
            apoyo_filtered = apoyo_qs.exclude(id__in=exclude_ids) if exclude_ids else apoyo_qs
            self.fields["ejecutivo_apoyo"] = forms.ModelChoiceField(
                queryset=apoyo_filtered.order_by("username"),
                required=False,
                empty_label="---------",
                widget=forms.Select(),
                label=self.fields["ejecutivo_apoyo"].label,
            )
            self.fields["ejecutivo_apoyo"].label_from_instance = _label_user

        if "comision_servicio" in self.fields:
            self.fields["comision_servicio"].required = False
            self.fields["comision_servicio"].disabled = True

        if _user_in_groups(self.user, ["Ejecutivo Jr", "Ejecutivo Apoyo"]):
            for field in self.fields.values():
                field.disabled = True
                field.required = False
        elif _user_in_groups(self.user, ["Ejecutivo Sr"]):
            for name, field in self.fields.items():
                if name != "ac":
                    field.disabled = True
                    field.required = False

        if self.instance and getattr(self.instance, "pk", None) and not self.is_bound:
            for i in range(1, 13):
                key = f"comision{i}"
                val = getattr(self.instance, key, None)
                if val is not None:
                    percent = (Decimal(val) * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                    self.initial[key] = format(percent, "f")
            total = Decimal("0")
            for i in range(1, 13):
                val = getattr(self.instance, f"comision{i}", None)
                if val is not None:
                    total += Decimal(val)
            percent = (total * Decimal(100)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            self.initial["comision_servicio"] = format(percent, "f")
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
            self.initial["comision_servicio"] = format(percent, "f")
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
        exec2_obj = cleaned.get("ejecutivo2")
        exec_id = exec_obj.id if exec_obj else None
        exec2_id = exec2_obj.id if exec2_obj else None
        apoyo = cleaned.get("ejecutivo_apoyo")

        if exec_id and exec2_id and exec_id == exec2_id:
            self.add_error("ejecutivo2", "Ejecutivo 2 no puede ser el mismo que Ejecutivo 1.")

        if apoyo and apoyo.id in {exec_id, exec2_id}:
            self.add_error("ejecutivo_apoyo", "El apoyo no puede ser el mismo que los ejecutivos principales.")

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
        return super().save(commit=commit)
