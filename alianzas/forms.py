from django import forms
from .models import Alianza

class AlianzaForm(forms.ModelForm):
    class Meta:
        model = Alianza
        fields = ['nombre', 'correo_electronico']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Asegurar que el correo sea obligatorio en el formulario, incluso si el modelo permite null.
        self.fields['correo_electronico'].required = True
