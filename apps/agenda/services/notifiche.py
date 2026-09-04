import ssl
import time
from datetime import time as dt_time

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.urls import reverse
from django.utils import timezone

from apps.agenda.models import ConfigurazioneNotificaEmail, EventoAgenda, LogNotificaEmail


SEND_WINDOW_MINUTES = 20
SMTP_SEND_PAUSE_SECONDS = 2.0
SMTP_MAX_ATTEMPTS = 3


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


DEFAULT_TEMPLATE_OGGETTO = "[Securtek] Promemoria {{data}} - {{titolo}}"
DEFAULT_TEMPLATE_CORPO = (
    "Promemoria: {{titolo}}\n"
    "\n"
    "Tipo: {{tipo}}\n"
    "Pratica: {{pratica_codice}} - {{pratica_titolo}}\n"
    "Cliente: {{cliente}}\n"
    "Data: {{data}}\n"
    "Ora: {{ora}}\n"
    "\n"
    "{{descrizione}}\n"
    "\n"
    "Apri pratica: {{url_pratica}}"
)


def build_event_context(evento, base_url):
    pratica = evento.pratica
    data_riferimento = evento.data_termine
    descrizione = (evento.descrizione or "").strip()
    ora = evento.ora_inizio.strftime("%H:%M") if evento.ora_inizio else ""
    data_notifica = evento.data_notifica
    return {
        "titolo": evento.titolo or "",
        "tipo": evento.get_tipo_display(),
        "pratica_codice": pratica.codice or "",
        "pratica_titolo": pratica.titolo or "",
        "cliente": str(pratica.cliente) if pratica.cliente_id else "",
        "data": data_riferimento.strftime("%d/%m/%Y") if data_riferimento else "",
        "ora": ora,
        "descrizione": descrizione,
        "url_pratica": f"{base_url}{reverse('pratiche:pratica_detail', kwargs={'pk': pratica.pk})}",
        "giorni_preavviso": str(evento.giorni_preavviso or ""),
        "data_notifica": data_notifica.strftime("%d/%m/%Y") if data_notifica else "",
    }


def render_mail_template(template_text, context, fallback=""):
    text = (template_text or "").strip() or fallback
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", str(value))
    # Evita righe vuote eccessive da {{ora}}/{{descrizione}} assenti.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip() + "\n"


def build_event_subject(evento, config=None, base_url=None):
    config = config or ConfigurazioneNotificaEmail.get_solo()
    base_url = base_url or get_site_base_url()
    context = build_event_context(evento, base_url)
    subject = render_mail_template(
        config.template_oggetto,
        context,
        fallback=DEFAULT_TEMPLATE_OGGETTO,
    ).strip()
    return subject[:300] or DEFAULT_TEMPLATE_OGGETTO


def build_event_message(evento, base_url=None, config=None):
    config = config or ConfigurazioneNotificaEmail.get_solo()
    base_url = base_url or get_site_base_url()
    context = build_event_context(evento, base_url)
    return render_mail_template(
        config.template_corpo,
        context,
        fallback=DEFAULT_TEMPLATE_CORPO,
    )


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
        # Include anche giorni saltati (Mac spento): data_notifica <= oggi
        if evento.data_notifica and evento.data_notifica <= today:
            due_events.append(evento)

    return due_events


def is_within_send_window(config, now=None, window_minutes=SEND_WINDOW_MINUTES):
    """True se l'ora locale e' nella finestra [ora_invio, ora_invio + window)."""
    now = timezone.localtime(now) if now else timezone.localtime()
    target = config.ora_invio or dt_time(8, 0)
    now_minutes = now.hour * 60 + now.minute
    target_minutes = target.hour * 60 + target.minute
    end_minutes = target_minutes + max(1, int(window_minutes))
    return target_minutes <= now_minutes < end_minutes


def format_smtp_error(exc, config=None):
    raw = str(exc)
    lowered = raw.lower()

    if "dovecot" in lowered or "imap4" in lowered or "+ok " in lowered:
        return (
            "Il server risponde come IMAP/POP3 (Dovecot), non come SMTP. "
            "Usa il server SMTP del provider (porta tipica 587 con TLS oppure 465 con SSL), "
            "non la porta IMAP (143/993) o POP3 (110/995)."
        )

    if "connection unexpectedly closed" in lowered or "connection reset" in lowered:
        return (
            "Il server SMTP ha chiuso la connessione durante l'invio. "
            "Di solito e' un limite del provider: riprova, oppure invia in orari non di punta. "
            f"Dettaglio tecnico: {raw}"
        )

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
        timeout=60,
    )
    if not getattr(config, "verifica_certificato_ssl", True):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection.ssl_context = context
    return connection


def is_smtp_connection_error(exc):
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "connection unexpectedly closed",
            "connection reset",
            "broken pipe",
            "server not connected",
            "please run connect()",
            "timed out",
            "timeout",
            "eof occurred",
        )
    )


def send_smtp_message(config, *, subject, body, recipients, max_attempts=SMTP_MAX_ATTEMPTS):
    """
    Invio robusto: nuova connessione per tentativo, pause e retry su errori di rete/SMTP.
    """
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        connection = None
        try:
            connection = get_smtp_connection(config)
            connection.open()
            message = EmailMessage(
                subject=subject,
                body=body,
                from_email=config.mittente,
                to=list(recipients),
                connection=connection,
            )
            message.send(fail_silently=False)
            return
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts or not is_smtp_connection_error(exc):
                raise
            time.sleep(SMTP_SEND_PAUSE_SECONDS * attempt)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
    if last_exc is not None:
        raise last_exc


def record_email_log(
    *,
    oggetto,
    destinatari,
    mittente="",
    esito=LogNotificaEmail.Esito.OK,
    tipo=LogNotificaEmail.Tipo.AUTOMATICA,
    evento=None,
    pratica=None,
    errore="",
    user=None,
):
    if isinstance(destinatari, (list, tuple, set)):
        destinatari_text = ", ".join(sorted({str(item).strip() for item in destinatari if str(item).strip()}))
    else:
        destinatari_text = str(destinatari or "").strip()

    return LogNotificaEmail.objects.create(
        inviata_il=timezone.now(),
        tipo=tipo,
        esito=esito,
        oggetto=(oggetto or "")[:300],
        destinatari=destinatari_text,
        mittente=(mittente or "")[:254],
        errore=(errore or "")[:4000],
        evento=evento,
        pratica=pratica or (evento.pratica if evento else None),
        created_by=user,
        updated_by=user,
    )


def send_test_email(config=None, recipients=None, user=None):
    """Invia una email di prova con i parametri SMTP salvati."""
    config = config or ConfigurazioneNotificaEmail.get_solo()
    recipients = sorted(
        {
            email.strip().lower()
            for email in (recipients or [])
            if email and str(email).strip()
        }
    )

    subject = "[Securtek] Email di test"
    if not config.host or not config.porta or not config.mittente:
        error = "Configura almeno server SMTP, porta e mittente, poi salva."
        record_email_log(
            oggetto=subject,
            destinatari=recipients,
            mittente=config.mittente,
            esito=LogNotificaEmail.Esito.ERRORE,
            tipo=LogNotificaEmail.Tipo.TEST,
            errore=error,
            user=user,
        )
        return {"ok": False, "error": error, "recipients": recipients}

    if config.porta in {110, 143, 993, 995}:
        error = (
            f"La porta {config.porta} e' tipica di IMAP/POP3, non di SMTP. "
            "Usa 587 (TLS) oppure 465 (SSL), poi salva e riprova."
        )
        record_email_log(
            oggetto=subject,
            destinatari=recipients,
            mittente=config.mittente,
            esito=LogNotificaEmail.Esito.ERRORE,
            tipo=LogNotificaEmail.Tipo.TEST,
            errore=error,
            user=user,
        )
        return {"ok": False, "error": error, "recipients": recipients}

    security_error = validate_smtp_security(config.porta, config.usa_tls, config.usa_ssl)
    if security_error:
        record_email_log(
            oggetto=subject,
            destinatari=recipients,
            mittente=config.mittente,
            esito=LogNotificaEmail.Esito.ERRORE,
            tipo=LogNotificaEmail.Tipo.TEST,
            errore=security_error,
            user=user,
        )
        return {"ok": False, "error": security_error, "recipients": recipients}

    if not recipients:
        error = "Indica un indirizzo email di destinazione."
        record_email_log(
            oggetto=subject,
            destinatari=[],
            mittente=config.mittente,
            esito=LogNotificaEmail.Esito.ERRORE,
            tipo=LogNotificaEmail.Tipo.TEST,
            errore=error,
            user=user,
        )
        return {"ok": False, "error": error, "recipients": []}

    body = (
        "Questa e' un'email di prova inviata da Securtek.\n"
        "Se l'hai ricevuta, i parametri SMTP sono configurati correttamente.\n"
    )

    try:
        send_smtp_message(
            config,
            subject=subject,
            body=body,
            recipients=recipients,
        )
    except Exception as exc:
        error = format_smtp_error(exc, config)
        record_email_log(
            oggetto=subject,
            destinatari=recipients,
            mittente=config.mittente,
            esito=LogNotificaEmail.Esito.ERRORE,
            tipo=LogNotificaEmail.Tipo.TEST,
            errore=error,
            user=user,
        )
        return {"ok": False, "error": error, "recipients": recipients}

    record_email_log(
        oggetto=subject,
        destinatari=recipients,
        mittente=config.mittente,
        esito=LogNotificaEmail.Esito.OK,
        tipo=LogNotificaEmail.Tipo.TEST,
        user=user,
    )
    return {"ok": True, "error": None, "recipients": recipients}


def send_agenda_notifications(dry_run=False, force=False):
    config = ConfigurazioneNotificaEmail.get_solo()

    if not config.servizio_attivo and not force and not dry_run:
        return {
            "skipped": "servizio_spento",
            "due": 0,
            "sent": 0,
            "errors": 0,
            "details": [],
        }

    if not config.attiva:
        return {
            "skipped": "config_disattivata",
            "due": 0,
            "sent": 0,
            "errors": 0,
            "details": [],
        }

    # La finestra oraria deve coprire almeno un ciclo di controllo.
    interval = max(1, int(getattr(config, "intervallo_controllo_minuti", None) or 15))
    window_minutes = max(SEND_WINDOW_MINUTES, interval + 1)

    if not force and not dry_run and not is_within_send_window(config, window_minutes=window_minutes):
        ora = config.ora_invio or dt_time(8, 0)
        return {
            "skipped": "fuori_orario",
            "ora_invio": ora.strftime("%H:%M"),
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

    for index, evento in enumerate(due_events):
        recipients = get_event_recipients(evento)
        subject = build_event_subject(evento, config=config, base_url=base_url)
        body = build_event_message(evento, base_url=base_url, config=config)

        if not recipients:
            errors += 1
            details.append({"evento_id": evento.pk, "status": "nessun_destinatario"})
            if not dry_run:
                record_email_log(
                    oggetto=subject,
                    destinatari=[],
                    mittente=config.mittente,
                    esito=LogNotificaEmail.Esito.SALTATA,
                    tipo=LogNotificaEmail.Tipo.AUTOMATICA,
                    evento=evento,
                    errore="Nessun destinatario disponibile",
                )
            continue

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
            record_email_log(
                oggetto=subject,
                destinatari=recipients,
                mittente=config.mittente,
                esito=LogNotificaEmail.Esito.DRY_RUN,
                tipo=LogNotificaEmail.Tipo.AUTOMATICA,
                evento=evento,
            )
            continue

        # Pausa tra un evento e il successivo: riduce i tagli del provider SMTP.
        if index > 0:
            time.sleep(SMTP_SEND_PAUSE_SECONDS)

        try:
            send_smtp_message(
                config,
                subject=subject,
                body=body,
                recipients=recipients,
            )
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
            record_email_log(
                oggetto=subject,
                destinatari=recipients,
                mittente=config.mittente,
                esito=LogNotificaEmail.Esito.OK,
                tipo=LogNotificaEmail.Tipo.AUTOMATICA,
                evento=evento,
            )
        except Exception as exc:
            errors += 1
            error = format_smtp_error(exc, config)
            details.append({"evento_id": evento.pk, "status": "error", "error": error})
            record_email_log(
                oggetto=subject,
                destinatari=recipients,
                mittente=config.mittente,
                esito=LogNotificaEmail.Esito.ERRORE,
                tipo=LogNotificaEmail.Tipo.AUTOMATICA,
                evento=evento,
                errore=error,
            )

    if not dry_run:
        config.ultimo_invio_il = timezone.now()
        config.ultimo_invio_esito = f"due={len(due_events)} sent={sent} errors={errors}"
        config.save(update_fields=["ultimo_invio_il", "ultimo_invio_esito", "updated_at"])

    return {
        "due": len(due_events),
        "sent": sent,
        "errors": errors,
        "details": details,
    }
