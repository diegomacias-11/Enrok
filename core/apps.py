from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Ejecuta hooks de arranque (ej. crear superusuario en Render)
        try:
            from .startup import ensure_superuser  # noqa
        except Exception:
            return
        ensure_superuser()
