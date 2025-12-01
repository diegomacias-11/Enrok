from django.db import models

class Alianza(models.Model):
    nombre = models.CharField(max_length=100)
    correo_electronico = models.EmailField(unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.nombre is not None:
            self.nombre = self.nombre.strip().upper()
        super().save(*args, **kwargs)
