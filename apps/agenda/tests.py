from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.mail import get_connection
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.agenda.forms import ConfigurazioneNotificaEmailForm
from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda
from apps.agenda.services.notifiche import get_due_events
from apps.anagrafiche.models import Anagrafica
from apps.pratiche.models import Pratica, Tecnico, TipologiaPratica


class GiorniPreavvisoTests(TestCase):
    def setUp(self):
        cliente = Anagrafica.objects.create(ragione_sociale="Cliente Test")
        tipologia = TipologiaPratica.objects.create(denominazione="Tipologia Test")
        self.pratica = Pratica.objects.create(
            titolo="Pratica test",
            cliente=cliente,
            tipologia=tipologia,
        )

    def _create_evento(self, **kwargs):
        defaults = {
            "pratica": self.pratica,
            "titolo": "Evento test",
            "notifica_email": True,
        }
        defaults.update(kwargs)
        return EventoAgenda.objects.create(**defaults)

    def test_due_when_notify_date_is_today(self):
        today = date(2026, 7, 11)
        evento = self._create_evento(
            data_inizio=today + timedelta(days=14),
            data_fine=today + timedelta(days=14),
            giorni_preavviso=7,
        )

        due = get_due_events(today=today)

        self.assertEqual(due, [evento])

    def test_not_due_before_notify_date(self):
        today = date(2026, 7, 10)
        self._create_evento(
            data_inizio=today + timedelta(days=14),
            data_fine=today + timedelta(days=14),
            giorni_preavviso=7,
        )

        self.assertEqual(get_due_events(today=today), [])

    def test_zero_preavviso_sends_on_deadline(self):
        today = date(2026, 7, 11)
        evento = self._create_evento(
            data_inizio=today,
            giorni_preavviso=0,
        )

        self.assertEqual(get_due_events(today=today), [evento])

    def test_uses_data_inizio_when_data_fine_missing(self):
        today = date(2026, 7, 4)
        evento = self._create_evento(
            data_inizio=today + timedelta(days=7),
            data_fine=None,
            giorni_preavviso=7,
        )

        self.assertEqual(get_due_events(today=today), [evento])
        self.assertEqual(evento.data_termine, evento.data_inizio)
        self.assertEqual(evento.data_notifica, today)


class ConfigurazioneNotificaEmailFormTests(TestCase):
    def setUp(self):
        self.config = ConfigurazioneNotificaEmail.get_solo()
        self.config.password = "password-esistente"
        self.config.host = "smtp.example.com"
        self.config.mittente = "noreply@example.com"
        self.config.save()

    def test_password_is_saved(self):
        form = ConfigurazioneNotificaEmailForm(
            data={
                "attiva": False,
                "servizio_attivo": True,
                "intervallo_controllo_minuti": 15,
                "host": "smtp.example.com",
                "porta": 587,
                "usa_tls": True,
                "usa_ssl": False,
                "verifica_certificato_ssl": True,
                "username": "user",
                "password": "nuova-password",
                "mittente": "noreply@example.com",
                "destinatari_default": "",
                "giorni_preavviso": 7,
                "ora_invio": "08:00",
                "note": "",
            },
            instance=self.config,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.config.refresh_from_db()
        self.assertEqual(self.config.password, "nuova-password")

    def test_blank_password_keeps_existing(self):
        form = ConfigurazioneNotificaEmailForm(
            data={
                "attiva": False,
                "servizio_attivo": True,
                "intervallo_controllo_minuti": 15,
                "host": "smtp.example.com",
                "porta": 587,
                "usa_tls": True,
                "usa_ssl": False,
                "verifica_certificato_ssl": True,
                "username": "user",
                "password": "",
                "mittente": "noreply@example.com",
                "destinatari_default": "",
                "giorni_preavviso": 7,
                "ora_invio": "08:00",
                "note": "",
            },
            instance=self.config,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.config.refresh_from_db()
        self.assertEqual(self.config.password, "password-esistente")

    def test_password_rendered_in_edit_form(self):
        form = ConfigurazioneNotificaEmailForm(instance=self.config)
        self.assertIn('value="password-esistente"', form.as_p())


class ConfigurazioneNotificaEmailViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="admin", password="secret")
        self.client.force_login(self.user)
        self.config = ConfigurazioneNotificaEmail.get_solo()

    def test_post_saves_password(self):
        response = self.client.post(
            reverse("agenda:configurazione_email"),
            {
                "attiva": False,
                "servizio_attivo": True,
                "intervallo_controllo_minuti": 15,
                "host": "smtp.example.com",
                "porta": 587,
                "usa_tls": True,
                "verifica_certificato_ssl": True,
                "username": "user",
                "password": "smtp-secret",
                "mittente": "noreply@example.com",
                "destinatari_default": "",
                "giorni_preavviso": 7,
                "ora_invio": "08:00",
                "note": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.config.refresh_from_db()
        self.assertEqual(self.config.password, "smtp-secret")

    def test_test_mail_requires_recipients(self):
        self.config.host = "smtp.example.com"
        self.config.porta = 587
        self.config.mittente = "noreply@example.com"
        self.config.save()

        response = self.client.post(reverse("agenda:configurazione_email_test"))

        self.assertRedirects(response, reverse("agenda:configurazione_email"))
        messages_list = [m.message for m in response.wsgi_request._messages]
        self.assertTrue(any("destinazione" in str(m).lower() for m in messages_list))

    def test_test_mail_rejects_invalid_email(self):
        self.config.host = "smtp.example.com"
        self.config.porta = 587
        self.config.mittente = "noreply@example.com"
        self.config.save()

        response = self.client.post(
            reverse("agenda:configurazione_email_test"),
            {"destinatario": "non-valida"},
        )

        self.assertRedirects(response, reverse("agenda:configurazione_email"))
        messages_list = [m.message for m in response.wsgi_request._messages]
        self.assertTrue(any("non e' valido" in str(m).lower() for m in messages_list))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("apps.agenda.services.notifiche.get_smtp_connection")
    def test_test_mail_sends_successfully(self, mock_connection):
        from django.core import mail

        mock_connection.side_effect = lambda config: get_connection(
            backend="django.core.mail.backends.locmem.EmailBackend"
        )

        self.config.host = "smtp.example.com"
        self.config.porta = 587
        self.config.mittente = "noreply@example.com"
        self.config.save()

        response = self.client.post(
            reverse("agenda:configurazione_email_test"),
            {"destinatario": "prova@example.com"},
        )

        self.assertRedirects(response, reverse("agenda:configurazione_email"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["prova@example.com"])
        self.assertIn("[Securtek] Email di test", mail.outbox[0].subject)


class EventoAgendaPersonaleClienteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="agenda", password="secret")
        self.client.force_login(self.user)

        self.cliente = Anagrafica.objects.create(ragione_sociale="Cliente Personale")
        tipologia = TipologiaPratica.objects.create(denominazione="Tipologia Personale")
        self.pratica_a = Pratica.objects.create(
            titolo="Pratica A",
            cliente=self.cliente,
            tipologia=tipologia,
        )
        self.pratica_b = Pratica.objects.create(
            titolo="Pratica B",
            cliente=self.cliente,
            tipologia=tipologia,
        )
        from apps.pratiche.models import Tecnico

        self.tecnico_a = Tecnico.objects.create(
            pratica=self.pratica_a,
            anagrafica=self.cliente,
            nome="Mario",
            cognome="Rossi",
            email="mario@example.com",
        )
        self.tecnico_b = Tecnico.objects.create(
            pratica=self.pratica_b,
            anagrafica=self.cliente,
            nome="Luigi",
            cognome="Bianchi",
            email="luigi@example.com",
        )
        self.tecnico_anagrafica = Tecnico.objects.create(
            anagrafica=self.cliente,
            pratica=None,
            nome="Anna",
            cognome="Verdi",
            email="anna@example.com",
        )

    def test_tecnici_endpoint_returns_cliente_personale(self):
        response = self.client.get(
            reverse("agenda:evento_tecnici"),
            {"pratica": self.pratica_b.pk},
        )

        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()["tecnici"]}
        self.assertIn(self.tecnico_a.pk, ids)
        self.assertIn(self.tecnico_b.pk, ids)
        self.assertIn(self.tecnico_anagrafica.pk, ids)

    def test_form_accepts_tecnico_from_anagrafica(self):
        from apps.agenda.forms import EventoAgendaForm

        form = EventoAgendaForm(
            data={
                "pratica": self.pratica_b.pk,
                "titolo": "Sopralluogo",
                "tipo": EventoAgenda.Tipo.LAVORO,
                "stato": EventoAgenda.Stato.PROGRAMMATO,
                "data_inizio": "2026-07-29",
                "tecnici": [self.tecnico_anagrafica.pk],
                "giorni_preavviso": 7,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        evento = form.save()
        self.assertEqual(
            list(evento.tecnici.values_list("pk", flat=True)),
            [self.tecnico_anagrafica.pk],
        )

    def test_anagrafica_personale_create(self):
        response = self.client.post(
            reverse("anagrafiche:personale_create", kwargs={"anagrafica_pk": self.cliente.pk}),
            {
                "nome": "Paolo",
                "cognome": "Neri",
                "email": "paolo@example.com",
                "telefono": "",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Tecnico.objects.filter(
                anagrafica=self.cliente,
                pratica__isnull=True,
                cognome="Neri",
                is_active=True,
            ).exists()
        )
