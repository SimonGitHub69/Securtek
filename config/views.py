from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from config.version import VERSION


def app_login_entry(request):
    """Ingresso app desktop (--app): attiva logout alla chiusura con X."""
    if request.GET.get("app") == "1":
        request.session["securtek_app"] = True
        request.session.modified = True

    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    return redirect(settings.LOGIN_URL)


@require_GET
def app_version(request):
    """Versione installata (per verifiche server/client)."""
    return JsonResponse(
        {
            "name": "securtek",
            "version": VERSION,
        }
    )


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(View):
    def _logout_and_respond(self, request):
        logout(request)

        silent = request.GET.get("silent") == "1"
        if silent:
            response = HttpResponse(status=204)
        else:
            response = redirect("admin:login")

        response["Cache-Control"] = "no-store"
        response.delete_cookie(
            settings.SESSION_COOKIE_NAME,
            path=getattr(settings, "SESSION_COOKIE_PATH", "/"),
            domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None) or None,
            samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax") or "Lax",
        )
        return response

    def post(self, request, *args, **kwargs):
        return self._logout_and_respond(request)

    def get(self, request, *args, **kwargs):
        return self._logout_and_respond(request)
