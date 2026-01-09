from __future__ import annotations

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import urlencode
import re


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Redirige a login si el usuario no esta autenticado, salvo rutas publicas.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return None

        resolver = getattr(request, "resolver_match", None)
        url_name = resolver.url_name if resolver else None
        public_names = {"login", "logout"}

        path = request.path
        if (
            (url_name in public_names)
            or path.startswith(settings.STATIC_URL)
            or path.startswith("/admin")
        ):
            return None

        login_url = settings.LOGIN_URL
        next_param = urlencode({"next": request.get_full_path()})
        return HttpResponseRedirect(f"{login_url}?{next_param}")


class GroupPermissionMiddleware(MiddlewareMixin):
    """
    Enforce permisos CRUD segun permisos de Django a nivel de URL.
    Infere accion/modelo desde el nombre de la URL y el app_label del view.
    """

    _IGNORE = {
        "lista", "list", "agregar", "add", "crear", "create", "editar", "update",
        "eliminar", "delete", "reporte", "reportes",
        "detalle", "detail", "ver",
    }

    def _infer_action(self, url_name: str) -> str:
        lower = url_name.lower()
        tokens = [t for t in re.split(r"[_-]+", lower) if t]
        if any(t in {"eliminar", "delete", "borrar"} for t in tokens):
            return "delete"
        if any(t in {"editar", "edit", "update", "actualizar", "cambiar"} for t in tokens):
            return "change"
        if any(t in {"agregar", "add", "crear", "create", "nuevo", "nueva", "registrar"} for t in tokens):
            return "add"
        return "view"

    def _infer_model(self, url_name: str) -> str:
        def _tokenize(text: str) -> list[str]:
            cleaned = re.sub(r"[^a-z0-9_]+", " ", (text or "").lower())
            return [p for p in cleaned.replace("_", " ").split() if p]

        tokens = _tokenize(url_name)
        app_label = getattr(self, "_current_app_label", None)
        models = []
        if app_label:
            try:
                models = list(apps.get_app_config(app_label).get_models())
            except Exception:
                models = []

        if tokens and models:
            token_set = set(tokens)
            candidates = []
            for model in models:
                model_tokens = set()
                model_tokens.update(_tokenize(model._meta.model_name))
                model_tokens.update(_tokenize(model._meta.verbose_name))
                model_tokens.update(_tokenize(model._meta.verbose_name_plural))
                overlap = model_tokens & token_set
                if overlap:
                    candidates.append((len(overlap), model._meta.model_name))
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                return candidates[0][1]
            if len(models) == 1:
                return models[0]._meta.model_name

        parts = [p for p in (url_name or "").lower().split("_") if p]
        base = ""
        for part in reversed(parts):
            if part not in self._IGNORE:
                base = part
                break
        if not base and parts:
            base = parts[-1]

        if base.endswith("es"):
            base = base[:-2]
        elif base.endswith("s"):
            base = base[:-1]
        return base

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        if user.is_superuser:
            return None

        path = request.path or ""
        if path.startswith("/admin"):
            return None

        resolver = getattr(request, "resolver_match", None)
        if not resolver or not resolver.url_name:
            return None

        public_names = {"login", "logout", "inicio"}
        if resolver.url_name in public_names:
            return None

        app_label = view_func.__module__.split(".")[0]
        self._current_app_label = app_label
        action = self._infer_action(resolver.url_name)
        model = self._infer_model(resolver.url_name)
        self._current_app_label = None

        if not model:
            if action in {"add", "change", "delete"}:
                return HttpResponse(
                    "<script>alert('No tienes permisos.'); window.history.back();</script>",
                    status=403,
                    content_type="text/html",
                )
            return None

        perm_code = f"{app_label}.{action}_{model}"
        perm_exists = Permission.objects.filter(
            content_type__app_label=app_label,
            codename=f"{action}_{model}",
        ).exists()

        if action in {"add", "change", "delete"} and not perm_exists:
            return HttpResponse(
                "<script>alert('No tienes permisos.'); window.history.back();</script>",
                status=403,
                content_type="text/html",
            )

        if not perm_exists:
            return None

        if user.has_perm(perm_code):
            return None

        return HttpResponse(
            "<script>alert('No tienes permisos.'); window.history.back();</script>",
            status=403,
            content_type="text/html",
        )
