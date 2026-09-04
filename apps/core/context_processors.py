from config.version import VERSION


def securtek_version(request):
    return {
        "SECURTEK_VERSION": VERSION,
        "SECURTEK_VERSION_LABEL": f"v. {VERSION}",
    }


def restore_scroll(request):
    """Espone restore_scroll_y da query ?scroll= o POST scroll_y (re-render form)."""
    raw = request.GET.get("scroll")
    if raw is None or raw == "":
        raw = request.POST.get("scroll_y")
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return {"restore_scroll_y": None}
    if value < 0 or value > 500_000:
        return {"restore_scroll_y": None}
    return {"restore_scroll_y": value}
