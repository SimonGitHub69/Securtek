from django.urls import path

from .views import (
    AnagraficaListView,
    AnagraficaCreateView,
    AnagraficaUpdateView,
)

app_name = "anagrfiche"

urlpatterns = [
    path("", AnagraficaListView.as_view(), name="anagrafica_list"),
    path("nuova/",AnagraficaCreateView.as_view(), name="anagrafica_create"),
    path("<int:pk>/modifica/", AnagraficaUpdateView.as_view(), name="anagrafica_update"),
]