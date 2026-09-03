#!/usr/bin/env python3
"""Helper locale Securtek: scegli/apri cartelle sul PC dove gira il browser.

Ascolta solo su 127.0.0.1. Il browser chiama questo servizio quando Django
è su un altro computer (es. Mac Mini server + PC Windows con D:/allegati).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 18765
HELPER_VERSION = 3

NATIVE_OPEN_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".xlsm"}
IGNORED_FOLDER_FILE_NAMES = {
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
    ".localized",
    ".spotlight-v100",
    ".trashes",
    ".fseventsd",
    ".temporaryitems",
}


def should_ignore_folder_file(file_path: Path) -> bool:
    name = file_path.name
    lower = name.lower()
    if lower in IGNORED_FOLDER_FILE_NAMES:
        return True
    if name.startswith("._"):
        return True
    return False


def office_file_priority(file_path: Path) -> int:
    return 0 if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS else 1


def format_file_datetime(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def pick_folder(title: str = "Seleziona cartella pratica") -> str | None:
    if sys.platform == "win32":
        safe = title.replace("'", "''")
        script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = '{safe}'
$dialog.ShowNewFolderButton = $true
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.SelectedPath
}}
"""
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-STA",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "Selettore Windows non disponibile.").strip())
        selected = (result.stdout or "").strip()
        return selected or None

    if sys.platform == "darwin":
        safe = title.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''
tell application "Finder"
    activate
end tell
try
    set chosenFolder to choose folder with prompt "{safe}"
    return POSIX path of chosenFolder
on error errMsg number errNum
    if errNum is -128 then
        return ""
    end if
    error errMsg number errNum
end try
'''
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            if "User canceled" in err or "-128" in err:
                return None
            raise RuntimeError(err or "Selettore macOS non disponibile.")
        selected = (result.stdout or "").strip().rstrip("/")
        return selected or None

    raise RuntimeError("Piattaforma non supportata dall'helper Securtek.")


def _macos_bring_finder_front() -> None:
    """Porta Finder in primo piano (davanti a Edge/Chrome in modalità app)."""
    scripts = [
        'tell application "Finder" to activate',
        'tell application "System Events" to set frontmost of process "Finder" to true',
    ]
    for script in scripts:
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            pass


def open_folder(path_value: str) -> None:
    folder = Path(path_value).expanduser()
    if not folder.exists():
        raise RuntimeError("Cartella non trovata su questo PC.")
    if not folder.is_dir():
        raise RuntimeError("Il percorso non è una cartella.")

    resolved = str(folder.resolve())
    if sys.platform == "win32":
        os.startfile(resolved)  # noqa: S606
        return
    if sys.platform == "darwin":
        safe = resolved.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''
set theFolder to POSIX file "{safe}"
tell application "Finder"
    activate
    open theFolder
    set target of front Finder window to theFolder
end tell
tell application "System Events"
    set frontmost of process "Finder" to true
end tell
'''
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fallback = subprocess.run(
                ["open", resolved],
                check=False,
                capture_output=True,
                text=True,
            )
            if fallback.returncode != 0:
                err = (result.stderr or result.stdout or fallback.stderr or "").strip()
                raise RuntimeError(err or "Impossibile aprire Finder.")
            _macos_bring_finder_front()
        return
    raise RuntimeError("Piattaforma non supportata dall'helper Securtek.")


def reveal_file(path_value: str) -> None:
    """Apre Explorer/Finder selezionando il file (Reveal in File Explorer)."""
    file_path = Path(path_value).expanduser()
    if not file_path.exists():
        raise RuntimeError("File non trovato su questo PC.")
    if not file_path.is_file():
        raise RuntimeError("Il percorso non è un file.")

    resolved = str(file_path.resolve())
    if sys.platform == "win32":
        subprocess.run(
            ["explorer.exe", "/select,", resolved],
            check=False,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return
    if sys.platform == "darwin":
        # AppleScript: reveal + activate in un colpo solo (più affidabile di open -R).
        safe = resolved.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''
set theItem to POSIX file "{safe}"
tell application "Finder"
    activate
    reveal theItem
    select theItem
end tell
tell application "System Events"
    set frontmost of process "Finder" to true
end tell
'''
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Fallback classico
            fallback = subprocess.run(
                ["open", "-R", resolved],
                check=False,
                capture_output=True,
                text=True,
            )
            if fallback.returncode != 0:
                err = (result.stderr or result.stdout or fallback.stderr or "").strip()
                raise RuntimeError(err or "Impossibile aprire Finder.")
            _macos_bring_finder_front()
        return
    raise RuntimeError("Piattaforma non supportata dall'helper Securtek.")


def list_folder(path_value: str) -> list[dict]:
    folder = Path(path_value).expanduser()
    if not folder.exists():
        raise RuntimeError("Cartella non trovata su questo computer.")
    if not folder.is_dir():
        raise RuntimeError("Il percorso non è una cartella.")

    entries: list[dict] = []
    for file_path in sorted(
        folder.rglob("*"),
        key=lambda item: (office_file_priority(item), str(item.relative_to(folder)).lower()),
    ):
        if not file_path.is_file() or should_ignore_folder_file(file_path):
            continue

        stat = file_path.stat()
        relative_path_text = file_path.relative_to(folder).as_posix()
        extension = file_path.suffix.upper().lstrip(".") or "-"
        entries.append(
            {
                "name": relative_path_text,
                "description": "",
                "extension": extension,
                "size_kb": max(1, round(stat.st_size / 1024)),
                "created_at": format_file_datetime(stat.st_ctime),
                "modified_at": format_file_datetime(stat.st_mtime),
                "full_path": str(file_path.resolve()),
                "url": "",
                "open_app_url": "",
                "preview_open_url": "",
                "description_url": "",
                "delete_url": "",
                "unlink_url": "",
                "open_folder_url": "",
            }
        )
    return entries


def _pick_ui_html(title: str, opener: str) -> bytes:
    """Pagina locale same-origin: aggira il blocco browser verso 127.0.0.1 dal server remoto."""
    payload = json.dumps(
        {
            "title": title or "Seleziona cartella pratica",
            "opener": opener or "*",
        },
        ensure_ascii=False,
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title></title>
<style>html,body{{margin:0;padding:0;width:1px;height:1px;overflow:hidden;opacity:0}}</style></head><body>
<script>
const cfg = {payload};
function notify(payload) {{
  if (window.opener && !window.opener.closed) {{
    try {{ window.opener.postMessage(payload, cfg.opener); }} catch (e) {{}}
  }}
  window.close();
}}
fetch("/pick-folder", {{
  method: "POST",
  headers: {{ "Content-Type": "application/json" }},
  body: JSON.stringify({{ title: cfg.title }}),
}})
  .then(function (r) {{ return r.json().then(function (d) {{ return {{ ok: r.ok, d: d }}; }}); }})
  .then(function (res) {{
    if (!res.ok || res.d.error) {{
      notify({{ type: "securtek-folder-picked", path: "", error: res.d.error || "Selezione fallita." }});
      return;
    }}
    notify({{
      type: "securtek-folder-picked",
      path: res.d.path || "",
      cancelled: !!res.d.cancelled || !res.d.path,
    }});
  }})
  .catch(function (err) {{
    notify({{ type: "securtek-folder-picked", path: "", error: (err && err.message) || "Helper non disponibile." }});
  }});
</script></body></html>"""
    return html.encode("utf-8")


def _list_ui_html(folder_path: str, opener: str) -> bytes:
    """Pagina locale same-origin per elencare file (come pick-ui)."""
    payload = json.dumps(
        {
            "path": folder_path or "",
            "opener": opener or "*",
        },
        ensure_ascii=False,
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title></title>
<style>html,body{{margin:0;padding:0;width:1px;height:1px;overflow:hidden;opacity:0}}</style></head><body>
<script>
const cfg = {payload};
function notify(payload) {{
  if (window.opener && !window.opener.closed) {{
    try {{ window.opener.postMessage(payload, cfg.opener); }} catch (e) {{}}
  }}
  window.close();
}}
if (!cfg.path) {{
  notify({{ type: "securtek-folder-list", files: [], error: "Percorso cartella mancante." }});
}} else {{
  fetch("/list-folder", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ path: cfg.path }}),
  }})
    .then(function (r) {{ return r.json().then(function (d) {{ return {{ ok: r.ok, d: d }}; }}); }})
    .then(function (res) {{
      if (!res.ok || res.d.error) {{
        notify({{ type: "securtek-folder-list", files: [], error: res.d.error || "Lettura fallita." }});
        return;
      }}
      notify({{ type: "securtek-folder-list", files: res.d.files || [], error: "" }});
    }})
    .catch(function (err) {{
      notify({{ type: "securtek-folder-list", files: [], error: (err && err.message) || "Helper non disponibile." }});
    }});
}}
</script></body></html>"""
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _cors(self) -> None:
        origin = self.headers.get("Origin") or "*"
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Access-Control-Request-Private-Network")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Vary", "Origin")

    def _reply(self, status: int, payload: dict) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/health":
            self._reply(
                200,
                {
                    "ok": True,
                    "service": "securtek-desktop-helper",
                    "version": HELPER_VERSION,
                    "platform": sys.platform,
                },
            )
            return
        if path == "/pick-ui":
            query = parse_qs(parsed.query)
            title = (query.get("title") or ["Seleziona cartella pratica"])[0]
            opener = (query.get("opener") or ["*"])[0]
            body = _pick_ui_html(title, opener)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/list-ui":
            query = parse_qs(parsed.query)
            folder = (query.get("path") or [""])[0]
            opener = (query.get("opener") or ["*"])[0]
            body = _list_ui_html(folder, opener)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return
        self._reply(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            data = {}

        try:
            if path == "/pick-folder":
                selected = pick_folder(str(data.get("title") or "Seleziona cartella pratica"))
                self._reply(200, {"path": selected or "", "cancelled": not bool(selected)})
                return
            if path == "/open-folder":
                folder = str(data.get("path") or "").strip()
                if not folder:
                    self._reply(400, {"error": "Percorso cartella mancante."})
                    return
                open_folder(folder)
                self._reply(200, {"ok": True, "message": f"Cartella aperta: {folder}"})
                return
            if path == "/reveal-file":
                file_path = str(data.get("path") or "").strip()
                if not file_path:
                    self._reply(400, {"error": "Percorso file mancante."})
                    return
                reveal_file(file_path)
                self._reply(200, {"ok": True, "message": f"File mostrato: {file_path}"})
                return
            if path == "/list-folder":
                folder = str(data.get("path") or "").strip()
                if not folder:
                    self._reply(400, {"error": "Percorso cartella mancante."})
                    return
                files = list_folder(folder)
                self._reply(200, {"files": files, "error": ""})
                return
        except Exception as exc:  # noqa: BLE001
            self._reply(500, {"error": str(exc)})
            return

        self._reply(404, {"error": "Not found"})


def main() -> int:
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        if getattr(exc, "errno", None) == 48 or "Address already in use" in str(exc):
            print(f"Helper già attivo su http://{HOST}:{PORT}/", flush=True)
            return 0
        raise
    print(f"Securtek desktop helper on http://{HOST}:{PORT}/ (v{HELPER_VERSION})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
