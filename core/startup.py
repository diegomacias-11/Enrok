"""
Hooks de arranque (se ejecutan cuando la app se carga).
Usado para crear un superusuario en Render cuando se define CREATE=1.
"""
from __future__ import annotations

import logging
import os
import sys

from django.contrib.auth import get_user_model
from django.db import connection

logger = logging.getLogger(__name__)


def ensure_superuser():
    """
    Crea un superusuario si CREATE=1 y se pasaron credenciales por entorno.

    Variables de entorno esperadas:
      - CREATE=1 (cualquier otro valor lo desactiva)
      - DJANGO_SUPERUSER_USERNAME
      - DJANGO_SUPERUSER_PASSWORD
      - DJANGO_SUPERUSER_EMAIL (opcional)
    """
    if os.environ.get("CREATE") != "1":
        return
    # Evitar ejecutar durante migraciones/creacion de tablas
    if any(cmd in sys.argv for cmd in ["migrate", "makemigrations", "collectstatic"]):
        return

    username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

    if not username or not password:
        logger.warning("CREATE=1 pero faltan credenciales de superusuario.")
        return

    User = get_user_model()
    # Saltar si las tablas auth aún no existen (primer arranque antes de migrate)
    try:
        if "auth_user" not in connection.introspection.table_names():
            return
    except Exception:
        return

    if User.objects.filter(username=username).exists():
        return

    try:
        User.objects.create_superuser(username=username, password=password, email=email)
        logger.info("Superusuario creado automaticamente (username=%s).", username)
    except Exception as exc:  # pragma: no cover
        logger.error("No se pudo crear el superusuario: %s", exc)
