from datetime import timedelta

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
        notify_date = evento.data_termine - timedelta(days=evento.giorni_preavviso)
        if notify_date == today:
            due_events.append(evento)

    return due_events


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
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=config.host,
            port=config.porta,
            username=config.username or None,
            password=config.password or None,
            use_tls=config.usa_tls,
            use_ssl=config.usa_ssl,
        )

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
            details.append({"evento_id": evento.pk, "status": "ok", "recipients": recipients})
        except Exception as exc:
            errors += 1
            details.append({"evento_id": evento.pk, "status": "error", "error": str(exc)})

    return {
        "due": len(due_events),
        "sent": sent,
        "errors": errors,
        "details": details,
    }
