from django.db.models.signals import post_save
from django.dispatch import receiver
from dispersiones.models import Dispersion
from .services import generar_comisiones_para_dispersion


@receiver(post_save, sender=Dispersion)
def generar_comisiones(sender, instance: Dispersion, created, **kwargs):
    generar_comisiones_para_dispersion(instance)
