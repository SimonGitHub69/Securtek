from django.urls import path
from .views import DashboardView, DocumentiView, SistemaView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="index"),
    path("documenti/", DocumentiView.as_view(), name="documenti"),
    path("sistema/", SistemaView.as_view(), name="sistema"),
]
