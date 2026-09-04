from functools import update_wrapper

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, redirect_to_login
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect


class SecurtekAdminLoginView(LoginView):
    """Staff → menu Django; altri utenti attivi → app."""

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse("admin:index")
        return settings.LOGIN_REDIRECT_URL

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[REDIRECT_FIELD_NAME] = self.get_success_url()
        return context


class SecurtekAdminSite(admin.AdminSite):
    site_header = "SECURTEK"
    site_title = "SECURTEK"
    index_title = "Amministrazione"

    def has_permission(self, request):
        return bool(request.user.is_active and request.user.is_staff)

    @method_decorator(never_cache)
    @login_not_required
    def login(self, request, extra_context=None):
        if request.method == "GET" and self.has_permission(request):
            return HttpResponseRedirect(reverse("admin:index", current_app=self.name))

        if request.user.is_authenticated and not self.has_permission(request):
            return redirect(settings.LOGIN_REDIRECT_URL)

        from django.contrib.auth.forms import AuthenticationForm

        context = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
            REDIRECT_FIELD_NAME: settings.LOGIN_REDIRECT_URL,
        }
        context.update(extra_context or {})

        defaults = {
            "extra_context": context,
            "authentication_form": self.login_form or AuthenticationForm,
            "template_name": self.login_template or "admin/login.html",
        }
        request.current_app = self.name
        return SecurtekAdminLoginView.as_view(**defaults)(request)

    def admin_view(self, view, cacheable=False):
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                login_path = reverse("admin:login", current_app=self.name)
                logout_path = reverse("admin:logout", current_app=self.name)
                if request.path == logout_path:
                    return HttpResponseRedirect(
                        reverse("admin:index", current_app=self.name)
                    )
                if request.user.is_authenticated:
                    return redirect(settings.LOGIN_REDIRECT_URL)
                if request.path == login_path:
                    return view(request, *args, **kwargs)
                return redirect_to_login(request.get_full_path(), login_path)
            return view(request, *args, **kwargs)

        if not cacheable:
            inner = never_cache(inner)
        if not getattr(view, "csrf_exempt", False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)
