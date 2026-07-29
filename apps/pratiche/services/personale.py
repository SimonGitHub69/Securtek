from django.db.models import Q

from apps.pratiche.models import Tecnico


def tecnici_per_cliente(cliente_id, pratica_id=None):
    """Personale dell'anagrafica cliente, inclusi quelli legati alle sue pratiche."""
    if not cliente_id and not pratica_id:
        return Tecnico.objects.none()

    filtri = Q()
    if cliente_id:
        filtri |= Q(anagrafica_id=cliente_id)
        filtri |= Q(pratica__cliente_id=cliente_id, pratica__is_active=True)
    if pratica_id:
        filtri |= Q(pratica_id=pratica_id)

    return (
        Tecnico.objects.filter(is_active=True)
        .filter(filtri)
        .select_related("studio_appartenenza", "incarico", "pratica", "anagrafica")
        .order_by("cognome", "nome", "id")
    )


def deduplica_tecnici(tecnici, prefer_pratica_id=None):
    seen = set()
    unique = []
    ordered = sorted(
        list(tecnici),
        key=lambda t: (
            0 if prefer_pratica_id and t.pratica_id == prefer_pratica_id else 1,
            0 if t.anagrafica_id and not t.pratica_id else 1,
            t.cognome or "",
            t.nome or "",
            t.pk or 0,
        ),
    )
    for tecnico in ordered:
        key = (
            (tecnico.cognome or "").strip().lower(),
            (tecnico.nome or "").strip().lower(),
            (tecnico.email or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(tecnico)
    return unique
