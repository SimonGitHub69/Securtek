#!/usr/bin/env python3
"""Helper locale Securtek: scegli/apri cartelle sul PC dove gira il browser.

Ascolta solo su 127.0.0.1. Il browser chiama questo servizio quando Django
è su un altro computer (es. Mac Mini server + PC Windows con D:/allegati).
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
PORT = 18765
HELPER_VERSION = 13
MAX_FOLDER_PREVIEW_FILES = 500
MAX_TRANSFER_BYTES = 80 * 1024 * 1024  # 80 MB per file via helper

_RESULT_STORE: dict[str, tuple[float, dict]] = {}
_RESULT_LOCK = threading.Lock()
_RESULT_TTL_SECONDS = 300

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


def normalize_client_path(path_value: str) -> str:
    """Normalizza path Mac/Windows tipici (typo /Volume/ → /Volumes/)."""
    text = (path_value or "").strip()
    if not text:
        return ""
    # Typo frequente: /Volume/... invece di /Volumes/...
    if text == "/Volume" or text.startswith("/Volume/"):
        text = "/Volumes" + text[len("/Volume") :]
    if text.startswith("~/"):
        text = str(Path(text).expanduser())
    # Uniforma slash finali su directory
    if len(text) > 3 and text.endswith("/") and not text.endswith("://"):
        text = text.rstrip("/")
    return text


def _applescript_quote(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace('"', '\\"')


def _default_volumes_location() -> str:
    volumes = Path("/Volumes")
    if volumes.is_dir():
        return str(volumes)
    return str(Path.home())


def _ensure_path_accessible(folder: Path) -> Path:
    """Sveglia mount e restituisce path normalizzato senza resolve aggressivo su SMB."""
    text = normalize_client_path(str(folder))
    path = Path(text).expanduser()
    if _is_network_volume_path(path):
        _wake_folder_access(path)
        time.sleep(0.35)
        _wake_folder_access(path)
    return path


def _list_files_via_shell_ls_as_user(folder: Path) -> list[Path]:
    """ls eseguito via osascript do shell script (contesto utente GUI, utile su SMB)."""
    if sys.platform != "darwin":
        return []
    safe = _applescript_quote(str(folder))
    script = f'''
try
    do shell script "/bin/ls -1A " & quoted form of "{safe}"
on error
    return ""
end try
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    found: list[Path] = []
    for line in (result.stdout or "").splitlines():
        name = line.strip()
        if not name or name in {".", ".."}:
            continue
        path = folder / name
        if should_ignore_folder_file(path):
            continue
        # Su SMB is_dir puo' fallire: se ha estensione trattalo come file.
        try:
            if path.is_dir():
                continue
        except OSError:
            if not path.suffix:
                continue
        found.append(path)
    return found


def _entry_is_dir(entry: os.DirEntry) -> bool:
    try:
        return entry.is_dir(follow_symlinks=False)
    except OSError:
        return False


def _entry_is_file(entry: os.DirEntry) -> bool:
    """True anche per placeholder cloud (Synology Drive / iCloud) che non passano is_file()."""
    try:
        if entry.is_file(follow_symlinks=False):
            return True
    except OSError:
        pass
    try:
        if entry.is_dir(follow_symlinks=False):
            return False
    except OSError:
        pass
    # File Provider / cloud: spesso né file né dir affidabili; con estensione = file.
    return bool(Path(entry.name).suffix)


def _iter_folder_files(folder: Path):
    """Elenco ricorsivo robusto (include file solo-online Synology Drive / File Provider)."""
    stack = [folder]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if should_ignore_folder_file(path):
                continue
            if _entry_is_dir(entry):
                stack.append(path)
                continue
            if _entry_is_file(entry):
                yield path


def _list_files_via_ls(folder: Path) -> list[Path]:
    """Fallback: /bin/ls (a volte vede voci che scandir non vede)."""
    try:
        result = subprocess.run(
            ["/bin/ls", "-1A", str(folder)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    found: list[Path] = []
    for line in (result.stdout or "").splitlines():
        name = line.strip()
        if not name or name in {".", ".."}:
            continue
        path = folder / name
        if should_ignore_folder_file(path):
            continue
        try:
            if path.is_dir():
                continue
        except OSError:
            # Senza info affidabile: includi solo se ha un'estensione (es. .pdf).
            if not path.suffix:
                continue
        found.append(path)
    return found


def _list_files_via_find(folder: Path, max_depth: int = 4) -> list[Path]:
    """Fallback find: spesso funziona su mount SMB /Volumes dove scandir e' vuoto."""
    try:
        result = subprocess.run(
            [
                "/usr/bin/find",
                str(folder),
                "-maxdepth",
                str(max_depth),
                "(",
                "-type",
                "f",
                "-o",
                "-type",
                "l",
                ")",
                "-print",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except Exception:
        return []
    if result.returncode not in (0, 1):
        # find ritorna 1 se alcuni path non sono accessibili ma puo' aver stampato risultati
        if not (result.stdout or "").strip():
            return []
    found: list[Path] = []
    seen: set[str] = set()
    for line in (result.stdout or "").splitlines():
        text = line.strip()
        if not text:
            continue
        path = Path(text)
        if should_ignore_folder_file(path):
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        found.append(path)
    return found


def _is_network_volume_path(folder: Path) -> bool:
    text = str(folder)
    if text.startswith("/Volumes/") or text == "/Volumes":
        return True
    if "CloudStorage" in text or "SynologyDrive" in text:
        return True
    return False


def _wake_folder_access(folder: Path) -> None:
    """Sveglia mount SMB/AFP e File Provider prima dell'elenco."""
    folder_text = str(folder)
    try:
        subprocess.run(
            ["/bin/ls", "-la", folder_text],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        pass
    if sys.platform != "darwin":
        return
    safe = folder_text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
set posixPath to "{safe}"
try
    tell application "Finder"
        set theFolder to (POSIX file posixPath) as alias
        open theFolder
        delay 0.4
        try
            close window 1
        end try
    end tell
end try
'''
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
    except Exception:
        pass


def _list_files_via_system_events(folder: Path) -> list[Path]:
    """System Events legge meglio i path POSIX su /Volumes rispetto a Finder alias."""
    if sys.platform != "darwin":
        return []
    safe = str(folder).replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
set posixPath to "{safe}"
set out to ""
try
    tell application "System Events"
        set theFolder to folder posixPath
        repeat with f in (every file of theFolder)
            try
                set out to out & (POSIX path of f) & linefeed
            end try
        end repeat
    end tell
end try
return out
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    found: list[Path] = []
    seen: set[str] = set()
    for line in (result.stdout or "").splitlines():
        text = line.strip().rstrip("/")
        if not text:
            continue
        path = Path(text)
        if should_ignore_folder_file(path):
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        found.append(path)
    return found


def _list_files_via_finder(folder: Path) -> list[Path]:
    """Fallback macOS: Finder vede /Volumes e CloudStorage meglio del processo Python."""
    if sys.platform != "darwin":
        return []
    safe = str(folder).replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
set posixPath to "{safe}"
set out to ""
tell application "Finder"
    try
        set theFolder to (POSIX file posixPath) as alias
    on error
        try
            set theFolder to folder posixPath
        on error
            return ""
        end try
    end try
    try
        open theFolder
        delay 0.3
    end try
    try
        update theFolder
    end try
    try
        repeat with f in (every file of theFolder)
            try
                set out to out & (POSIX path of (f as alias)) & linefeed
            end try
        end repeat
    end try
    try
        repeat with f in (every document file of theFolder)
            try
                set out to out & (POSIX path of (f as alias)) & linefeed
            end try
        end repeat
    end try
    if out is "" then
        try
            repeat with f in (every item of theFolder)
                try
                    if class of f is folder then
                    else
                        set out to out & (POSIX path of (f as alias)) & linefeed
                    end if
                end try
            end repeat
        end try
    end if
    if out is "" then
        try
            repeat with f in (every file of entire contents of theFolder)
                try
                    set out to out & (POSIX path of (f as alias)) & linefeed
                end try
            end repeat
        end try
    end if
    try
        close window 1
    end try
end tell
return out
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except Exception:
        return []
    if result.returncode != 0:
        return []
    found: list[Path] = []
    seen: set[str] = set()
    for line in (result.stdout or "").splitlines():
        text = line.strip().rstrip("/")
        if not text:
            continue
        path = Path(text)
        if should_ignore_folder_file(path):
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        found.append(path)
    return found


def _merge_unique_paths(*groups: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for group in groups:
        for path in group:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            found.append(path)
    return found


def _collect_folder_files(folder: Path) -> list[Path]:
    """Elenco robusto: /Volumes (SMB) e CloudStorage richiedono fallback multipli."""
    folder = Path(normalize_client_path(str(folder)))
    networkish = _is_network_volume_path(folder)
    if networkish:
        _wake_folder_access(folder)
        time.sleep(0.25)

    scandir_files = list(_iter_folder_files(folder))
    if scandir_files and not networkish:
        return scandir_files

    # Su /Volumes e CloudStorage: non fidarsi di scandir vuoto o parziale.
    finder_files: list[Path] = []
    system_events_files: list[Path] = []
    shell_ls_files: list[Path] = []
    ls_files: list[Path] = []
    find_files: list[Path] = []

    if sys.platform == "darwin":
        finder_files = _list_files_via_finder(folder)
        if not finder_files:
            system_events_files = _list_files_via_system_events(folder)
        if not finder_files and not system_events_files:
            shell_ls_files = _list_files_via_shell_ls_as_user(folder)

    ls_files = _list_files_via_ls(folder)
    if not ls_files or networkish:
        find_files = _list_files_via_find(folder)

    merged = _merge_unique_paths(
        scandir_files,
        finder_files,
        system_events_files,
        shell_ls_files,
        ls_files,
        find_files,
    )
    # Secondo tentativo dopo altra sveglia del mount.
    if not merged and networkish:
        _wake_folder_access(folder)
        time.sleep(0.6)
        merged = _merge_unique_paths(
            _list_files_via_finder(folder),
            _list_files_via_system_events(folder),
            _list_files_via_shell_ls_as_user(folder),
            _list_files_via_ls(folder),
            _list_files_via_find(folder),
        )
    return merged


def office_file_priority(file_path: Path) -> int:
    return 0 if file_path.suffix.lower() in NATIVE_OPEN_EXTENSIONS else 1


def format_file_datetime(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M")


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _resolve_win_pick_folder_script() -> Path:
    here = Path(__file__).resolve().parent
    local = here / "win_pick_folder.py"
    if local.is_file():
        return local
    for parent in (here, *here.parents):
        candidate = parent / "scripts" / "win_pick_folder.py"
        if candidate.is_file():
            return candidate
    raise RuntimeError("Script win_pick_folder.py non trovato accanto all'helper.")


def _python_gui_executable() -> str:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.is_file():
        return str(pythonw)
    return str(exe)


def pick_folder(
    title: str = "Seleziona cartella pratica",
    default_path: str | None = None,
) -> str | None:
    if sys.platform == "win32":
        script_path = _resolve_win_pick_folder_script()
        # Nessun CREATE_NO_WINDOW: il processo figlio deve poter mostrare il dialogo nativo.
        result = subprocess.run(
            [
                _python_gui_executable(),
                str(script_path),
                title,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "Selettore Windows non disponibile.").strip())
        selected = normalize_client_path((result.stdout or "").strip())
        return selected or None

    if sys.platform == "darwin":
        safe_title = _applescript_quote(title)
        start = normalize_client_path(default_path or "") or _default_volumes_location()
        # Se il default e' un file, usa la cartella padre.
        start_path = Path(start)
        if start_path.is_file():
            start = str(start_path.parent)
        elif not start_path.exists():
            # Preferisci /Volumes se la cartella indicata non e' ancora montata.
            start = _default_volumes_location()
        safe_start = _applescript_quote(start)
        script = f'''
tell application "Finder"
    activate
end tell
try
    set defaultLoc to POSIX file "{safe_start}"
    set chosenFolder to choose folder with prompt "{safe_title}" default location defaultLoc
    return POSIX path of chosenFolder
on error errMsg number errNum
    if errNum is -128 then
        return ""
    end if
    -- Riprova senza default location (alcuni mount SMB falliscono sul default).
    try
        set chosenFolder to choose folder with prompt "{safe_title}"
        return POSIX path of chosenFolder
    on error errMsg2 number errNum2
        if errNum2 is -128 then
            return ""
        end if
        error errMsg2 number errNum2
    end try
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
        selected = normalize_client_path((result.stdout or "").strip())
        if selected and _is_network_volume_path(Path(selected)):
            _wake_folder_access(Path(selected))
        return selected or None

    raise RuntimeError("Piattaforma non supportata dall'helper Securtek.")


def pick_file(
    title: str = "Seleziona file da collegare",
    default_path: str | None = None,
) -> str | None:
    """Selettore file nativo sul computer locale (client)."""
    if sys.platform == "win32":
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Selettore file non disponibile: {exc}") from exc
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        initial = normalize_client_path(default_path or "") or None
        try:
            selected = filedialog.askopenfilename(
                title=title,
                initialdir=initial,
                filetypes=[
                    (
                        "File supportati",
                        "*.doc *.docx *.xls *.xlsx *.xlsm *.pdf *.png *.jpg *.jpeg *.txt *.html *.htm",
                    ),
                    ("Tutti i file", "*.*"),
                ],
            )
        finally:
            root.destroy()
        return normalize_client_path(selected or "") or None

    if sys.platform == "darwin":
        safe_title = _applescript_quote(title)
        start = normalize_client_path(default_path or "") or _default_volumes_location()
        start_path = Path(start)
        if start_path.is_file():
            start = str(start_path.parent)
        elif not start_path.exists():
            start = _default_volumes_location()
        if _is_network_volume_path(Path(start)):
            _wake_folder_access(Path(start))
        safe_start = _applescript_quote(start)
        script = f'''
tell application "Finder"
    activate
end tell
try
    set defaultLoc to POSIX file "{safe_start}"
    set chosenFile to choose file with prompt "{safe_title}" default location defaultLoc
    return POSIX path of chosenFile
on error errMsg number errNum
    if errNum is -128 then
        return ""
    end if
    try
        set chosenFile to choose file with prompt "{safe_title}"
        return POSIX path of chosenFile
    on error errMsg2 number errNum2
        if errNum2 is -128 then
            return ""
        end if
        error errMsg2 number errNum2
    end try
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
            raise RuntimeError(err or "Selettore file macOS non disponibile.")
        selected = normalize_client_path((result.stdout or "").strip())
        return selected or None

    raise RuntimeError("Piattaforma non supportata dall'helper Securtek.")


def write_file_to_folder(folder_value: str, file_name: str, content_b64: str) -> str:
    """Scrive un file nella cartella locale (anche /Volumes SMB)."""
    folder = _ensure_path_accessible(Path(normalize_client_path(folder_value)))
    name = Path(file_name or "").name
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise RuntimeError("Nome file non valido.")
    if not folder.exists() or not folder.is_dir():
        raise RuntimeError(
            "Cartella di destinazione non trovata su questo computer. "
            "Apri /Volumes/tmp1 in Finder e riprova."
        )

    raw = base64.b64decode(content_b64 or "", validate=False)
    if len(raw) > MAX_TRANSFER_BYTES:
        raise RuntimeError("File troppo grande per il trasferimento locale (max 80 MB).")

    # Evita resolve() aggressivo su SMB (puo' fallire o cambiare il path).
    target = folder / name
    try:
        if target.exists():
            raise RuntimeError(f"Esiste gia' un file con questo nome: {name}")
    except OSError:
        pass

    target.write_bytes(raw)
    return str(target)


def read_file_bytes(path_value: str) -> tuple[str, bytes]:
    file_path = Path(normalize_client_path(path_value)).expanduser()
    if _is_network_volume_path(file_path.parent):
        _wake_folder_access(file_path.parent)
    if not file_path.exists() or not file_path.is_file():
        raise RuntimeError("File non trovato su questo computer.")
    data = file_path.read_bytes()
    if len(data) > MAX_TRANSFER_BYTES:
        raise RuntimeError("File troppo grande per il trasferimento locale (max 80 MB).")
    return file_path.name, data


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


def open_file(path_value: str) -> None:
    """Apre il file con l'applicazione predefinita sul computer locale."""
    file_path = Path(path_value).expanduser()
    if not file_path.exists():
        raise RuntimeError("File non trovato su questo PC.")
    if not file_path.is_file():
        raise RuntimeError("Il percorso non è un file.")

    resolved = str(file_path.resolve())
    if sys.platform == "win32":
        os.startfile(resolved)  # noqa: S606
        return
    if sys.platform == "darwin":
        result = subprocess.run(
            ["open", resolved],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(err or "Impossibile aprire il file.")
        return
    raise RuntimeError("Piattaforma non supportata dall'helper Securtek.")


def _store_popup_result(result_id: str, payload: dict) -> None:
    if not result_id:
        return
    with _RESULT_LOCK:
        _RESULT_STORE[result_id] = (time.time(), payload)


def _take_popup_result(result_id: str) -> dict | None:
    if not result_id:
        return None
    with _RESULT_LOCK:
        entry = _RESULT_STORE.pop(result_id, None)
    if not entry:
        return None
    return entry[1]


def _cleanup_popup_results() -> None:
    cutoff = time.time() - _RESULT_TTL_SECONDS
    with _RESULT_LOCK:
        stale = [key for key, (created, _) in _RESULT_STORE.items() if created < cutoff]
        for key in stale:
            _RESULT_STORE.pop(key, None)


def list_folder(path_value: str) -> tuple[list[dict], bool]:
    folder = Path(normalize_client_path(path_value)).expanduser()
    networkish = _is_network_volume_path(folder)

    # Mount SMB a volte non risultano "exists" finche' non li tocchi.
    if not folder.exists() and networkish:
        _wake_folder_access(folder)
        time.sleep(0.4)

    if not folder.exists():
        raise RuntimeError(
            "Cartella non trovata su questo computer. "
            "Per condivisioni tipo /Volumes/tmp1: aprila una volta in Finder, "
            "poi riprova Scegli in Securtek."
        )
    if not folder.is_dir():
        raise RuntimeError("Il percorso non è una cartella.")

    entries: list[dict] = []
    truncated = False
    files = sorted(
        _collect_folder_files(folder),
        key=lambda item: (office_file_priority(item), str(item).lower()),
    )

    # Se ancora vuota su CloudStorage /Volumes, messaggio operativo chiaro.
    if not files:
        folder_text = str(folder)
        if "CloudStorage" in folder_text or "SynologyDrive" in folder_text:
            raise RuntimeError(
                "Nessun file letto in Synology Drive / CloudStorage. "
                "Apri Impostazioni di Sistema → Privacy e sicurezza → Accesso disco completo "
                "e aggiungi Python (o Terminale), poi rilancia InstallClient. "
                "In alternativa: in Synology Drive rendi la cartella disponibile offline."
            )
        if folder_text.startswith("/Volumes/"):
            raise RuntimeError(
                "Nessun file letto su questa condivisione di rete (/Volumes). "
                "Apri la cartella una volta in Finder, verifica che sia montata, "
                "poi in Impostazioni → Privacy e sicurezza → Accesso disco completo "
                "aggiungi Python e rilancia InstallClient. "
                "Se la cartella e' sul Mac Mini, preferisci un path Synology Drive o una copia locale."
            )

    for file_path in files:
        try:
            relative_path_text = file_path.relative_to(folder).as_posix()
        except ValueError:
            relative_path_text = file_path.name

        try:
            stat = file_path.stat()
            size_kb = max(1, round(stat.st_size / 1024))
            created_at = format_file_datetime(stat.st_ctime)
            modified_at = format_file_datetime(stat.st_mtime)
        except OSError:
            size_kb = 0
            created_at = "-"
            modified_at = "-"

        try:
            full_path = str(file_path.resolve())
        except OSError:
            full_path = str(file_path)

        extension = file_path.suffix.upper().lstrip(".") or "-"
        entries.append(
            {
                "name": relative_path_text,
                "description": "",
                "extension": extension,
                "size_kb": size_kb,
                "created_at": created_at,
                "modified_at": modified_at,
                "full_path": full_path,
                "url": "",
                "open_app_url": "",
                "preview_open_url": "",
                "description_url": "",
                "delete_url": "",
                "unlink_url": "",
                "open_folder_url": "",
            }
        )
        if len(entries) >= MAX_FOLDER_PREVIEW_FILES:
            truncated = True
            break
    return entries, truncated


def _pick_ui_html(title: str, opener: str, callback: str, default_path: str = "") -> bytes:
    """Pagina locale same-origin: aggira il blocco browser verso 127.0.0.1 dal server remoto."""
    payload = json.dumps(
        {
            "title": title or "Seleziona cartella pratica",
            "opener": opener or "*",
            "callback": callback or "",
            "default_path": default_path or "",
        },
        ensure_ascii=False,
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title></title>
<style>html,body{{margin:0;padding:0;width:1px;height:1px;overflow:hidden;opacity:0}}</style></head><body>
<script>
const cfg = {payload};
function storeResult(payload) {{
  if (!cfg.callback) return Promise.resolve();
  return fetch("/result", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ id: cfg.callback, payload: payload }}),
  }}).catch(function () {{}});
}}
function notify(payload) {{
  storeResult(payload).finally(function () {{
    if (window.opener && !window.opener.closed) {{
      try {{ window.opener.postMessage(payload, cfg.opener); }} catch (e) {{}}
    }}
    window.close();
  }});
}}
fetch("/pick-folder", {{
  method: "POST",
  headers: {{ "Content-Type": "application/json" }},
  body: JSON.stringify({{ title: cfg.title, default_path: cfg.default_path || "" }}),
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
      files: res.d.files || [],
      truncated: !!res.d.truncated,
    }});
  }})
  .catch(function (err) {{
    notify({{ type: "securtek-folder-picked", path: "", error: (err && err.message) || "Helper non disponibile." }});
  }});
</script></body></html>"""
    return html.encode("utf-8")


def _list_ui_html(folder_path: str, opener: str, callback: str) -> bytes:
    """Pagina locale same-origin per elencare file (come pick-ui)."""
    payload = json.dumps(
        {
            "path": folder_path or "",
            "opener": opener or "*",
            "callback": callback or "",
        },
        ensure_ascii=False,
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title></title>
<style>html,body{{margin:0;padding:0;width:1px;height:1px;overflow:hidden;opacity:0}}</style></head><body>
<script>
const cfg = {payload};
function storeResult(payload) {{
  if (!cfg.callback) return Promise.resolve();
  return fetch("/result", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ id: cfg.callback, payload: payload }}),
  }}).catch(function () {{}});
}}
function notify(payload) {{
  storeResult(payload).finally(function () {{
    if (window.opener && !window.opener.closed) {{
      try {{ window.opener.postMessage(payload, cfg.opener); }} catch (e) {{}}
    }}
    window.close();
  }});
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
      notify({{
        type: "securtek-folder-list",
        files: res.d.files || [],
        truncated: !!res.d.truncated,
        error: "",
      }});
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
            callback = (query.get("cb") or [""])[0]
            default_path = (query.get("default") or [""])[0]
            body = _pick_ui_html(title, opener, callback, default_path)
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
            callback = (query.get("cb") or [""])[0]
            body = _list_ui_html(folder, opener, callback)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/result":
            query = parse_qs(parsed.query)
            result_id = (query.get("id") or [""])[0]
            _cleanup_popup_results()
            payload = _take_popup_result(result_id)
            if payload is None:
                self._reply(404, {"payload": None})
                return
            self._reply(200, {"payload": payload})
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
            if path == "/result":
                result_id = str(data.get("id") or "").strip()
                payload = data.get("payload")
                if not result_id or not isinstance(payload, dict):
                    self._reply(400, {"error": "Risultato popup non valido."})
                    return
                _cleanup_popup_results()
                _store_popup_result(result_id, payload)
                self._reply(200, {"ok": True})
                return
            if path == "/pick-folder":
                selected = pick_folder(
                    str(data.get("title") or "Seleziona cartella pratica"),
                    default_path=str(data.get("default_path") or "").strip() or None,
                )
                files: list[dict] = []
                truncated = False
                if selected:
                    try:
                        files, truncated = list_folder(selected)
                    except Exception:  # noqa: BLE001
                        files, truncated = [], False
                self._reply(
                    200,
                    {
                        "path": selected or "",
                        "cancelled": not bool(selected),
                        "files": files,
                        "truncated": truncated,
                    },
                )
                return
            if path == "/pick-file":
                selected = pick_file(
                    str(data.get("title") or "Seleziona file da collegare"),
                    default_path=str(data.get("default_path") or "").strip() or None,
                )
                self._reply(
                    200,
                    {
                        "path": selected or "",
                        "cancelled": not bool(selected),
                        "name": Path(selected).name if selected else "",
                    },
                )
                return
            if path == "/list-folder":
                folder = normalize_client_path(str(data.get("path") or "").strip())
                if not folder:
                    self._reply(400, {"error": "Percorso cartella mancante."})
                    return
                files, truncated = list_folder(folder)
                self._reply(200, {"files": files, "error": "", "truncated": truncated})
                return
            if path == "/write-file":
                folder = normalize_client_path(str(data.get("folder") or "").strip())
                name = str(data.get("name") or "").strip()
                content_b64 = str(data.get("content_b64") or "")
                if not folder or not name or not content_b64:
                    self._reply(400, {"error": "Parametri write-file incompleti."})
                    return
                written = write_file_to_folder(folder, name, content_b64)
                self._reply(200, {"ok": True, "path": written, "name": Path(written).name})
                return
            if path == "/read-file":
                file_path = normalize_client_path(str(data.get("path") or "").strip())
                if not file_path:
                    self._reply(400, {"error": "Percorso file mancante."})
                    return
                name, raw = read_file_bytes(file_path)
                self._reply(
                    200,
                    {
                        "ok": True,
                        "name": name,
                        "content_b64": base64.b64encode(raw).decode("ascii"),
                        "size": len(raw),
                    },
                )
                return
            if path == "/open-folder":
                folder = normalize_client_path(str(data.get("path") or "").strip())
                if not folder:
                    self._reply(400, {"error": "Percorso cartella mancante."})
                    return
                open_folder(folder)
                self._reply(200, {"ok": True, "message": f"Cartella aperta: {folder}"})
                return
            if path == "/reveal-file":
                file_path = normalize_client_path(str(data.get("path") or "").strip())
                if not file_path:
                    self._reply(400, {"error": "Percorso file mancante."})
                    return
                reveal_file(file_path)
                self._reply(200, {"ok": True, "message": f"File mostrato: {file_path}"})
                return
            if path == "/open-file":
                file_path = normalize_client_path(str(data.get("path") or "").strip())
                if not file_path:
                    self._reply(400, {"error": "Percorso file mancante."})
                    return
                open_file(file_path)
                self._reply(200, {"ok": True, "message": f"File aperto: {file_path}"})
                return
        except Exception as exc:  # noqa: BLE001
            self._reply(500, {"error": str(exc)})
            return

        self._reply(404, {"error": "Not found"})


def main() -> int:
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        in_use = (
            getattr(exc, "winerror", None) == 10048
            or getattr(exc, "errno", None) in (48, 98, 10048)
            or "Address already in use" in str(exc)
        )
        if in_use:
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
