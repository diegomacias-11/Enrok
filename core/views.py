from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import logout


def inicio(request):
    if request.user.is_authenticated:
        return redirect("dispersiones_lista")
    return redirect(settings.LOGIN_URL)


def logout_view(request):
    logout(request)
    next_url = request.GET.get("next") or settings.LOGOUT_REDIRECT_URL or settings.LOGIN_URL
    return redirect(next_url)
