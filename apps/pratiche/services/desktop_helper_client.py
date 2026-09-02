"""Client HTTP verso l'helper desktop locale (127.0.0.1:18765)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

HELPER_BASE = "http://127.0.0.1:18765"
HELPER_VERSION_MIN = 1


class DesktopHelperError(RuntimeError):
    """Helper locale non disponibile o in errore."""


def helper_health(timeout: float = 2.0) -> bool:
    request = urllib.request.Request(f"{HELPER_BASE}/health", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return bool(data.get("ok")) and int(data.get("version") or 0) >= HELPER_VERSION_MIN
    except Exception:
        return False


def _post(path: str, payload: dict, timeout: float = 180.0) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{HELPER_BASE}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(detail)
            message = data.get("error") or detail
        except json.JSONDecodeError:
            message = detail or str(exc)
        raise DesktopHelperError(message) from exc
    except Exception as exc:
        raise DesktopHelperError(
            "Helper desktop non disponibile. "
            "Su Mac server: ./deploy/macos/install-desktop-helper.sh. "
            "Su Mac client: deploy/macos-client/InstallClient.command."
        ) from exc


def pick_folder_via_helper(title: str = "Seleziona cartella pratica") -> str | None:
    if not helper_health():
        raise DesktopHelperError("Helper desktop non in ascolto.")
    data = _post("/pick-folder", {"title": title}, timeout=300.0)
    if data.get("error"):
        raise DesktopHelperError(str(data["error"]))
    path = (data.get("path") or "").strip()
    return path or None


def open_folder_via_helper(path: str) -> str:
    if not helper_health():
        raise DesktopHelperError("Helper desktop non in ascolto.")
    data = _post("/open-folder", {"path": path}, timeout=30.0)
    if data.get("error"):
        raise DesktopHelperError(str(data["error"]))
    return str(data.get("message") or f"Cartella aperta: {path}")


def reveal_file_via_helper(path: str) -> str:
    if not helper_health():
        raise DesktopHelperError("Helper desktop non in ascolto.")
    data = _post("/reveal-file", {"path": path}, timeout=30.0)
    if data.get("error"):
        raise DesktopHelperError(str(data["error"]))
    return str(data.get("message") or f"File mostrato: {path}")


def list_folder_via_helper(path: str) -> list[dict]:
    if not helper_health():
        raise DesktopHelperError("Helper desktop non in ascolto.")
    data = _post("/list-folder", {"path": path}, timeout=60.0)
    if data.get("error"):
        raise DesktopHelperError(str(data["error"]))
    return list(data.get("files") or [])
