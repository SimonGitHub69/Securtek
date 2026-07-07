from django.views.generic import TemplateView

from apps.anagrafiche.models import Anagrafica


class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["kpi"] = {
            "anagrafiche": Anagrafica.objects.filter(is_active=True).count(),
            "pratiche": 0,
            "documenti": 0,
            "scadenze": 0,
        }

        return context