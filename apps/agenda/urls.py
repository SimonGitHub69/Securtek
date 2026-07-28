from django.urls import path

from apps.agenda.views import (
    AgendaCalendarView,
    AgendaDayView,
    ConfigurazioneNotificaEmailTestView,
    ConfigurazioneNotificaEmailUpdateView,
    EventoAgendaCreateView,
    EventoAgendaDeleteView,
    EventoAgendaTecniciView,
    EventoAgendaUpdateView,
)

app_name = "agenda"

urlpatterns = [
    path("", AgendaCalendarView.as_view(), name="calendar"),
    path("giorno/", AgendaDayView.as_view(), name="day"),
    path("parametri-mail/", ConfigurazioneNotificaEmailUpdateView.as_view(), name="configurazione_email"),
    path(
        "parametri-mail/test/",
        ConfigurazioneNotificaEmailTestView.as_view(),
        name="configurazione_email_test",
    ),
    path("tecnici/", EventoAgendaTecniciView.as_view(), name="evento_tecnici"),
    path("nuovo/", EventoAgendaCreateView.as_view(), name="evento_create"),
    path("<int:pk>/modifica/", EventoAgendaUpdateView.as_view(), name="evento_update"),
    path("<int:pk>/elimina/", EventoAgendaDeleteView.as_view(), name="evento_delete"),
]
