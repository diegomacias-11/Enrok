from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import logout


def inicio(request):
    if request.user.is_authenticated:
        return redirect("dispersiones_list")
    return redirect(settings.LOGIN_URL)


def logout_view(request):
    logout(request)
    next_url = request.GET.get("next") or settings.LOGOUT_REDIRECT_URL or settings.LOGIN_URL
    return redirect(next_url)


def csrf_failure(request, reason=""):
    return render(
        request,
        "errors/csrf.html",
        {"reason": reason},
        status=403,
    )
