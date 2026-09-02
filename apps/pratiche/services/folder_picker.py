"""Native folder/file pickers for the local desktop (no tkinter required).

Used by Django views that block the request until the user picks a path.
The server process must run on the same machine as the interactive desktop session.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class FolderPickerError(OSError):
    """Raised when a native folder/file picker cannot be opened."""


def _platform_key() -> str:
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform == "win32":
        return "win32"
    return "linux"


def _windows_no_window_kwargs() -> dict:
    kwargs: dict = {}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    kwargs["startupinfo"] = startupinfo
    return kwargs


def _escape_ps_single_quoted(value: str) -> str:
    return value.replace("'", "''")


def _windows_pick_folder_script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "win_pick_folder.py"


def _python_gui_executable() -> str:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.is_file():
        return str(pythonw)
    return str(exe)


def _run_powershell(script: str, *, ui: bool = False) -> str:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-STA",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    kwargs: dict = _windows_no_window_kwargs()
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
    except FileNotFoundError as exc:
        raise FolderPickerError("PowerShell non disponibile su questo sistema.") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise FolderPickerError(detail or "Selettore Windows non disponibile.")

    return (result.stdout or "").strip()


def _run_powershell_file(script_path: Path, *args: str) -> str:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-STA",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        *args,
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_windows_no_window_kwargs(),
        )
    except FileNotFoundError as exc:
        raise FolderPickerError("PowerShell non disponibile su questo sistema.") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise FolderPickerError(detail or "Selettore Windows non disponibile.")

    return (result.stdout or "").strip()


def _pick_folder_windows(title: str) -> str | None:
    script_path = _windows_pick_folder_script_path()
    if not script_path.is_file():
        raise FolderPickerError(f"Script selettore non trovato: {script_path}")
    try:
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
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        raise FolderPickerError("Timeout selezione cartella Windows.") from exc
    except FileNotFoundError as exc:
        raise FolderPickerError("Python non disponibile per il selettore cartelle.") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise FolderPickerError(detail or "Selettore Windows non disponibile.")
    selected = (result.stdout or "").strip()
    return selected or None


def _pick_file_windows(title: str, filetypes: list[tuple[str, str]] | None = None) -> str | None:
    safe_title = _escape_ps_single_quoted(title)
    filters: list[str] = []
    for label, pattern in filetypes or []:
        filters.append(f"{_escape_ps_single_quoted(label)}|{pattern.replace(' ', ';')}")
    filters.append("Tutti i file|*.*")
    filter_text = _escape_ps_single_quoted("|".join(filters))
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = '{safe_title}'
$dialog.Filter = '{filter_text}'
$dialog.Multiselect = $false
$dialog.CheckFileExists = $true
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $dialog.FileName
}}
"""
    selected = _run_powershell(script, ui=True)
    return selected or None


def _pick_folder_macos(title: str) -> str | None:
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    script = f'''
tell application "Finder"
    activate
end tell
try
    set chosenFolder to choose folder with prompt "{safe_title}"
    return POSIX path of chosenFolder
on error errMsg number errNum
    if errNum is -128 then
        return ""
    end if
    error errMsg number errNum
end try
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise FolderPickerError("osascript non disponibile su questo sistema.") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if "user canceled" in stderr or "user cancelled" in stderr or "-128" in stderr:
            return None
        raise FolderPickerError(
            (result.stderr or result.stdout or "").strip()
            or "Selettore macOS non disponibile. Avvia l'helper desktop."
        )

    selected = (result.stdout or "").strip()
    return selected.rstrip("/") if selected else None


def _pick_file_macos(title: str, filetypes: list[tuple[str, str]] | None = None) -> str | None:
    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    extensions: list[str] = []
    for _label, pattern in filetypes or []:
        for token in pattern.replace(";", " ").split():
            token = token.strip().lstrip("*").lstrip(".")
            if token and token != "*" and token not in extensions:
                extensions.append(token)

    if extensions:
        ext_list = ", ".join(f'"{ext}"' for ext in extensions)
        script = (
            f'set theFile to choose file with prompt "{safe_title}" '
            f"of type {{{ext_list}}}\n"
            "POSIX path of theFile"
        )
    else:
        script = (
            f'set theFile to choose file with prompt "{safe_title}"\n'
            "POSIX path of theFile"
        )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise FolderPickerError("osascript non disponibile su questo sistema.") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").lower()
        if "user canceled" in stderr or "user cancelled" in stderr:
            return None
        raise FolderPickerError((result.stderr or result.stdout or "").strip() or "Selettore macOS non disponibile.")

    selected = (result.stdout or "").strip()
    return selected or None


def _pick_folder_linux(title: str) -> str | None:
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise FolderPickerError(
            "Ambiente grafico non disponibile. "
            "Il server deve essere avviato sulla postazione locale con GUI attiva."
        )

    zenity = shutil.which("zenity")
    if zenity:
        result = subprocess.run(
            [zenity, "--file-selection", "--directory", f"--title={title}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip() or None
        if result.returncode == 1:
            return None
        raise FolderPickerError((result.stderr or "").strip() or "Selettore zenity non disponibile.")

    kdialog = shutil.which("kdialog")
    if kdialog:
        result = subprocess.run(
            [kdialog, "--getexistingdirectory", ".", "--title", title],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip() or None
        if result.returncode == 1:
            return None
        raise FolderPickerError((result.stderr or "").strip() or "Selettore kdialog non disponibile.")

    raise FolderPickerError("Installa zenity o kdialog, oppure usa un Python con tkinter.")


def _pick_file_linux(title: str, filetypes: list[tuple[str, str]] | None = None) -> str | None:
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise FolderPickerError(
            "Ambiente grafico non disponibile. "
            "Il server deve essere avviato sulla postazione locale con GUI attiva."
        )

    zenity = shutil.which("zenity")
    if zenity:
        command = [zenity, "--file-selection", f"--title={title}"]
        for label, pattern in filetypes or []:
            command.append(f"--file-filter={label} | {pattern}")
        command.append("--file-filter=Tutti i file | *")
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode == 0:
            return (result.stdout or "").strip() or None
        if result.returncode == 1:
            return None
        raise FolderPickerError((result.stderr or "").strip() or "Selettore zenity non disponibile.")

    kdialog = shutil.which("kdialog")
    if kdialog:
        result = subprocess.run(
            [kdialog, "--getopenfilename", ".", "--title", title],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip() or None
        if result.returncode == 1:
            return None
        raise FolderPickerError((result.stderr or "").strip() or "Selettore kdialog non disponibile.")

    raise FolderPickerError("Installa zenity o kdialog, oppure usa un Python con tkinter.")


def _pick_folder_tkinter(title: str) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise FolderPickerError(f"Selettore cartella non disponibile: {exc}") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        selected = filedialog.askdirectory(title=title)
    finally:
        root.destroy()
    return selected or None


def _pick_file_tkinter(title: str, filetypes: list[tuple[str, str]] | None = None) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise FolderPickerError(f"Selettore file non disponibile: {exc}") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        selected = filedialog.askopenfilename(title=title, filetypes=filetypes or [("Tutti i file", "*.*")])
    finally:
        root.destroy()
    return selected or None


def pick_folder(title: str = "Seleziona cartella") -> str | None:
    """Open a native folder dialog and return the selected path, or None if cancelled."""
    platform = _platform_key()
    try:
        if platform == "win32":
            return _pick_folder_windows(title)
        if platform == "darwin":
            return _pick_folder_macos(title)
        return _pick_folder_linux(title)
    except FolderPickerError as native_exc:
        try:
            return _pick_folder_tkinter(title)
        except FolderPickerError:
            raise native_exc from None


def pick_file(
    title: str = "Seleziona file",
    filetypes: list[tuple[str, str]] | None = None,
) -> str | None:
    """Open a native file dialog and return the selected path, or None if cancelled."""
    platform = _platform_key()
    try:
        if platform == "win32":
            return _pick_file_windows(title, filetypes)
        if platform == "darwin":
            return _pick_file_macos(title, filetypes)
        return _pick_file_linux(title, filetypes)
    except FolderPickerError as native_exc:
        try:
            return _pick_file_tkinter(title, filetypes)
        except FolderPickerError:
            raise native_exc from None


def normalize_selected_path(selected: str | None) -> str:
    if not selected:
        return ""
    return str(Path(selected).expanduser())
