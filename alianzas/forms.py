from django import forms
from .models import Alianza

class AlianzaForm(forms.ModelForm):
    class Meta:
        model = Alianza
        fields = ['nombre', 'correo_electronico']
