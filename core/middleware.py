from __future__ import annotations

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import urlencode


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
