import ssl

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.urls import reverse
from django.utils import timezone

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda


def parse_destinatari(text):
    for part in (text or "").replace(",", "\n").splitlines():
        email = part.strip()
        if email:
            yield email


def get_site_base_url():
    return getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def get_event_recipients(evento):
    recipients = set()

    for tecnico in evento.tecnici.filter(is_active=True):
        if tecnico.email:
            recipients.add(tecnico.email.strip().lower())

    responsabile = evento.pratica.responsabile
    if responsabile and responsabile.email:
        recipients.add(responsabile.email.strip().lower())

    config = ConfigurazioneNotificaEmail.get_solo()
    for email in parse_destinatari(config.destinatari_default):
        recipients.add(email.lower())

    return sorted(recipients)


def build_event_message(evento, base_url):
    pratica = evento.pratica
    data_riferimento = evento.data_termine
    lines = [
        f"Promemoria: {evento.titolo}",
        "",
        f"Tipo: {evento.get_tipo_display()}",
        f"Pratica: {pratica.codice} - {pratica.titolo}",
        f"Cliente: {pratica.cliente}",
        f"Data: {data_riferimento:%d/%m/%Y}",
    ]

    if evento.ora_inizio:
        lines.append(f"Ora: {evento.ora_inizio:%H:%M}")

    if evento.descrizione:
        lines.extend(["", evento.descrizione])

    pratica_url = f"{base_url}{reverse('pratiche:pratica_detail', kwargs={'pk': pratica.pk})}"
    lines.extend(["", f"Apri pratica: {pratica_url}"])

    return "\n".join(lines)


def get_due_events(today=None):
    today = today or timezone.localdate()
    queryset = (
        EventoAgenda.objects.filter(
            is_active=True,
            notifica_email=True,
            notificato_il__isnull=True,
        )
        .exclude(stato__in=[EventoAgenda.Stato.COMPLETATO, EventoAgenda.Stato.ANNULLATO])
        .select_related("pratica", "pratica__cliente", "pratica__responsabile")
        .prefetch_related("tecnici")
    )

    due_events = []
    for evento in queryset:
        if evento.data_notifica == today:
            due_events.append(evento)

    return due_events


def format_smtp_error(exc, config=None):
    raw = str(exc)
    lowered = raw.lower()

    if "dovecot" in lowered or "imap4" in lowered or "+ok " in lowered:
        return (
            "Il server risponde come IMAP/POP3 (Dovecot), non come SMTP. "
            "Usa il server SMTP del provider (porta tipica 587 con TLS oppure 465 con SSL), "
            "non la porta IMAP (143/993) o POP3 (110/995)."
        )

    if "wrong_version_number" in lowered or "wrong version number" in lowered:
        porta = getattr(config, "porta", None)
        if porta == 587:
            return (
                "Mismatch TLS/SSL sulla porta 587: disattiva SSL e attiva TLS (STARTTLS), "
                "poi salva e riprova."
            )
        if porta == 465:
            return (
                "Mismatch TLS/SSL sulla porta 465: disattiva TLS e attiva SSL, "
                "poi salva e riprova."
            )
        return (
            "Mismatch TLS/SSL: porta 587 → TLS sì / SSL no; "
            "porta 465 → SSL sì / TLS no."
        )

    if "certificate_verify_failed" in lowered or "hostname mismatch" in lowered:
        return (
            "Certificato SSL non valido per il server SMTP indicato. "
            "Usa l'hostname corretto del certificato, oppure disattiva "
            "\"Verifica certificato SSL\", salva e riprova."
        )

    if "authentication" in lowered or ("auth" in lowered and ("fail" in lowered or "invalid" in lowered)):
        return f"Autenticazione SMTP fallita: {raw}"

    return raw


def validate_smtp_security(porta, usa_tls, usa_ssl):
    """Restituisce un messaggio di errore se porta e TLS/SSL non coincidono."""
    if usa_tls and usa_ssl:
        return "TLS e SSL non possono essere attivi insieme."

    if porta == 587 and usa_ssl:
        return "Porta 587: attiva TLS e disattiva SSL."

    if porta == 465 and usa_tls:
        return "Porta 465: attiva SSL e disattiva TLS."

    if porta == 587 and not usa_tls and not usa_ssl:
        return "Porta 587: attiva TLS (STARTTLS)."

    if porta == 465 and not usa_ssl:
        return "Porta 465: attiva SSL."

    return None


def get_smtp_connection(config):
    connection = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=config.host,
        port=config.porta,
        username=config.username or None,
        password=config.password or None,
        use_tls=config.usa_tls,
        use_ssl=config.usa_ssl,
    )
    if not getattr(config, "verifica_certificato_ssl", True):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection.ssl_context = context
    return connection


def send_test_email(config=None, recipients=None):
    """Invia una email di prova con i parametri SMTP salvati."""
    config = config or ConfigurazioneNotificaEmail.get_solo()
    recipients = sorted(
        {
            email.strip().lower()
            for email in (recipients or [])
            if email and str(email).strip()
        }
    )

    if not config.host or not config.porta or not config.mittente:
        return {
            "ok": False,
            "error": "Configura almeno server SMTP, porta e mittente, poi salva.",
            "recipients": recipients,
        }

    if config.porta in {110, 143, 993, 995}:
        return {
            "ok": False,
            "error": (
                f"La porta {config.porta} e' tipica di IMAP/POP3, non di SMTP. "
                "Usa 587 (TLS) oppure 465 (SSL), poi salva e riprova."
            ),
            "recipients": recipients,
        }

    security_error = validate_smtp_security(config.porta, config.usa_tls, config.usa_ssl)
    if security_error:
        return {
            "ok": False,
            "error": security_error,
            "recipients": recipients,
        }

    if not recipients:
        return {
            "ok": False,
            "error": "Indica un indirizzo email di destinazione.",
            "recipients": [],
        }

    subject = "[Securtek] Email di test"
    body = (
        "Questa e' un'email di prova inviata da Securtek.\n"
        "Se l'hai ricevuta, i parametri SMTP sono configurati correttamente.\n"
    )

    try:
        connection = get_smtp_connection(config)
        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=config.mittente,
            to=recipients,
            connection=connection,
        )
        message.send()
    except Exception as exc:
        return {
            "ok": False,
            "error": format_smtp_error(exc, config),
            "recipients": recipients,
        }

    return {
        "ok": True,
        "error": None,
        "recipients": recipients,
    }


def send_agenda_notifications(dry_run=False):
    config = ConfigurazioneNotificaEmail.get_solo()

    if not config.attiva:
        return {
            "skipped": "config_disattivata",
            "due": 0,
            "sent": 0,
            "errors": 0,
            "details": [],
        }

    due_events = get_due_events()
    base_url = get_site_base_url()
    sent = 0
    errors = 0
    details = []

    connection = None
    if not dry_run:
        connection = get_smtp_connection(config)

    for evento in due_events:
        recipients = get_event_recipients(evento)

        if not recipients:
            errors += 1
            details.append({"evento_id": evento.pk, "status": "nessun_destinatario"})
            continue

        subject = f"[Securtek] Promemoria {evento.data_termine:%d/%m/%Y} - {evento.titolo}"
        body = build_event_message(evento, base_url)

        if dry_run:
            sent += 1
            details.append(
                {
                    "evento_id": evento.pk,
                    "status": "dry_run",
                    "recipients": recipients,
                    "data_termine": evento.data_termine,
                    "data_notifica": evento.data_notifica,
                    "giorni_preavviso": evento.giorni_preavviso,
                }
            )
            continue

        try:
            message = EmailMessage(
                subject=subject,
                body=body,
                from_email=config.mittente,
                to=recipients,
                connection=connection,
            )
            message.send()
            evento.notificato_il = timezone.now()
            evento.save(update_fields=["notificato_il", "updated_at"])
            sent += 1
            details.append(
                {
                    "evento_id": evento.pk,
                    "status": "ok",
                    "recipients": recipients,
                    "data_termine": evento.data_termine,
                    "data_notifica": evento.data_notifica,
                    "giorni_preavviso": evento.giorni_preavviso,
                }
            )
        except Exception as exc:
            errors += 1
            details.append({"evento_id": evento.pk, "status": "error", "error": str(exc)})

    return {
        "due": len(due_events),
        "sent": sent,
        "errors": errors,
        "details": details,
    }
