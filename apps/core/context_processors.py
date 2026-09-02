from config.version import VERSION


def securtek_version(request):
    return {
        "SECURTEK_VERSION": VERSION,
        "SECURTEK_VERSION_LABEL": f"v. {VERSION}",
    }
