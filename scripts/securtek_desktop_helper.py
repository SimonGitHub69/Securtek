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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 18765
HELPER_VERSION = 1


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
        path = urlparse(self.path).path
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
        except Exception as exc:  # noqa: BLE001
            self._reply(500, {"error": str(exc)})
            return

        self._reply(404, {"error": "Not found"})


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Securtek desktop helper on http://{HOST}:{PORT}/ (v{HELPER_VERSION})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
