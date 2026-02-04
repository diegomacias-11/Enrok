from django.db.models.signals import post_save
from django.dispatch import receiver
from dispersiones.models import Dispersion
from dispersiones_servicios.models import Dispersion as DispersionServicio
from .services import generar_comisiones_para_dispersion, generar_comisiones_para_dispersion_servicios


@receiver(post_save, sender=Dispersion)
def generar_comisiones(sender, instance: Dispersion, created, **kwargs):
    generar_comisiones_para_dispersion(instance)


@receiver(post_save, sender=DispersionServicio)
def generar_comisiones_servicios(sender, instance: DispersionServicio, created, **kwargs):
    generar_comisiones_para_dispersion_servicios(instance)
