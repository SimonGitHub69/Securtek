from django.urls import path

from .views import (
    AnagraficaListView,
    AnagraficaCreateView,
    AnagraficaUpdateView,
    AnagraficaDetailView,
)

app_name = "anagrafiche"

urlpatterns = [
    path("", AnagraficaListView.as_view(), name="anagrafica_list"),
    path("nuova/",AnagraficaCreateView.as_view(), name="anagrafica_create"),
    path("<int:pk>/modifica/", AnagraficaUpdateView.as_view(), name="anagrafica_update"),
    path("<int:pk>/", AnagraficaDetailView.as_view(), name="anagrafica_detail"),
]