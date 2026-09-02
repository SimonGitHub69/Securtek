"""Open files and folders on the local desktop (Windows, macOS, Linux).

Foreground on Windows uses ctypes (AttachThreadInput + SetForegroundWindow) in a
daemon thread after explorer.exe Popen. We deliberately avoid PowerShell/cmd
helpers: they spawn a visible console window (black flash) and still fail Windows
foreground rules when launched from a background Django process.

The Django server process must run on the same machine where files live and where
the user expects Finder/Explorer to appear. Remote servers cannot open paths on
the client browser machine.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


class DesktopOpenError(OSError):
    """Raised when a desktop open action cannot be completed."""


def _platform_key() -> str:
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform == "win32":
        return "win32"
    return "linux"


def _resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _require_command(name: str, *, human_name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise DesktopOpenError(f"{human_name} non disponibile su questo sistema.")
    return executable


def _run_command(
    command: list[str],
    *,
    no_window_kwargs: dict | None = None,
    use_popen: bool = False,
) -> None:
    kwargs = no_window_kwargs or {}
    try:
        if use_popen:
            subprocess.Popen(command, **kwargs)
            return

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            **kwargs,
        )
    except FileNotFoundError as exc:
        raise DesktopOpenError("Comando desktop non disponibile su questo sistema.") from exc

    if use_popen:
        return

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if not detail and _platform_key() == "linux" and not _linux_has_display():
            detail = (
                "Ambiente grafico non disponibile. "
                "Il server deve essere avviato sulla postazione locale con GUI attiva."
            )
        raise DesktopOpenError(detail or "Impossibile completare l'apertura desktop.")


def _linux_has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _windows_explorer_exe() -> str:
    system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    return os.path.join(system_root, "explorer.exe")


def folder_open_success_message(item_name: str) -> str:
    """User-facing success text after opening a folder in the file manager."""
    base = f"Cartella aperta per: {item_name}"
    platform = _platform_key()
    if platform == "win32":
        # Foreground attempted via ctypes in background; taskbar hint lives in JS fallback.
        return base
    if platform == "darwin":
        return f"{base}. Se non vedi Finder in primo piano, controlla il Dock."
    return base


def _windows_title_hints_for_path(path: Path) -> list[str]:
    hints: list[str] = []
    for candidate in (path.name, str(path), path.stem):
        if candidate and candidate not in hints:
            hints.append(candidate)
    if path.parent != path:
        for candidate in (path.parent.name, str(path.parent)):
            if candidate and candidate not in hints:
                hints.append(candidate)
    return hints


def _windows_collect_explorer_windows() -> dict[int, dict[str, object]]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    windows: dict[int, dict[str, object]] = {}

    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if class_name.value == "CabinetWClass":
                length = user32.GetWindowTextLengthW(hwnd)
                title = ""
                if length > 0:
                    title_buffer = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, title_buffer, length + 1)
                    title = title_buffer.value
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                windows[int(hwnd)] = {"title": title, "pid": pid.value}
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return windows


def _windows_find_explorer_hwnd(
    before_windows: dict[int, dict[str, object]],
    *,
    title_hints: list[str],
) -> int | None:
    after_windows = _windows_collect_explorer_windows()
    new_hwnds = set(after_windows) - set(before_windows)
    if new_hwnds:
        return max(new_hwnds)

    lowered_hints = [hint.lower() for hint in title_hints if hint]
    for hwnd, info in after_windows.items():
        title = str(info.get("title", "")).lower()
        if any(hint in title for hint in lowered_hints):
            return hwnd

    if after_windows:
        return max(after_windows)
    return None


def _windows_bring_to_foreground(hwnd: int) -> bool:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    KEYEVENTF_KEYUP = 2
    VK_MENU = 0x12

    foreground_hwnd = user32.GetForegroundWindow()
    foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    attached = False
    if foreground_thread and target_thread and foreground_thread != target_thread:
        attached = bool(user32.AttachThreadInput(foreground_thread, target_thread, True))

    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.keybd_event(VK_MENU, 0, 0, 0)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    ok = bool(user32.SetForegroundWindow(hwnd))
    user32.BringWindowToTop(hwnd)

    if attached:
        user32.AttachThreadInput(foreground_thread, target_thread, False)
    return ok


def _windows_schedule_explorer_foreground(
    *,
    before_windows: dict[int, dict[str, object]],
    title_hints: list[str],
) -> None:
    """Try to raise Explorer without subprocess helpers (no black flash)."""

    def worker() -> None:
        try:
            time.sleep(0.5)
            chosen = _windows_find_explorer_hwnd(before_windows, title_hints=title_hints)
            if not chosen:
                time.sleep(0.3)
                chosen = _windows_find_explorer_hwnd(before_windows, title_hints=title_hints)
            if chosen:
                _windows_bring_to_foreground(chosen)
        except Exception:
            pass

    threading.Thread(
        target=worker,
        daemon=True,
        name="securtek-explorer-foreground",
    ).start()


def _windows_open_explorer_select(file_path: Path) -> None:
    target = os.path.normpath(str(file_path.resolve()))
    before_windows = _windows_collect_explorer_windows()
    subprocess.Popen(
        [_windows_explorer_exe(), "/select,", target],
        shell=False,
    )
    _windows_schedule_explorer_foreground(
        before_windows=before_windows,
        title_hints=_windows_title_hints_for_path(file_path),
    )


def _windows_open_folder(folder_path: Path) -> None:
    target = os.path.normpath(str(folder_path.resolve()))
    before_windows = _windows_collect_explorer_windows()
    subprocess.Popen(
        [_windows_explorer_exe(), target],
        shell=False,
    )
    _windows_schedule_explorer_foreground(
        before_windows=before_windows,
        title_hints=_windows_title_hints_for_path(folder_path),
    )


def _windows_open_default_app(file_path: Path) -> None:
    os.startfile(str(file_path))


def _macos_open(*args: str) -> None:
    _require_command("open", human_name="Comando open (macOS)")
    _run_command(["open", *args])
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to activate'],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to set frontmost of process "Finder" to true',
            ],
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def _macos_open_file_in_finder(file_path: Path) -> None:
    target = str(file_path.resolve())
    safe = target.replace("\\", "\\\\").replace('"', '\\"')
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
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise DesktopOpenError("osascript non disponibile su questo sistema.") from exc

    if result.returncode != 0:
        _macos_open("-R", target)


def _macos_open_folder(folder_path: Path) -> None:
    path_text = str(folder_path)
    if re.match(r"^[A-Za-z]:[\\/]", path_text) or path_text.startswith("\\\\"):
        raise DesktopOpenError(
            "Percorso Windows non valido sul Mac. "
            "Usa Scegli cartella per selezionare un percorso Mac, "
            "oppure apri Securtek dal PC Windows."
        )
    target = str(folder_path.resolve())
    safe = target.replace("\\", "\\\\").replace('"', '\\"')
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
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise DesktopOpenError("osascript non disponibile su questo sistema.") from exc

    if result.returncode != 0:
        _macos_open(target)


def _macos_open_file_with_default_app(file_path: Path) -> None:
    _macos_open(str(file_path))


def _linux_open_path(path: Path) -> None:
    if not _linux_has_display():
        raise DesktopOpenError(
            "Ambiente grafico non disponibile. "
            "Il server deve essere avviato sulla postazione locale con GUI attiva."
        )
    executable = _require_command("xdg-open", human_name="xdg-open")
    _run_command([executable, str(path)])


def open_file_in_explorer(file_path: str | Path) -> None:
    """Open the system file manager and reveal ``file_path`` when supported."""
    selected = _resolve_path(file_path)
    if not selected.is_file():
        raise DesktopOpenError("File non trovato")

    platform = _platform_key()
    if platform == "win32":
        _windows_open_explorer_select(selected)
        return
    if platform == "darwin":
        _macos_open_file_in_finder(selected)
        return

    _linux_open_path(selected.parent)


def open_folder_in_explorer(folder_path: str | Path) -> None:
    """Open ``folder_path`` in the system file manager."""
    folder = _resolve_path(folder_path)
    if not folder.exists():
        raise DesktopOpenError("Cartella non trovata")
    if not folder.is_dir():
        raise DesktopOpenError("Il percorso non è una cartella")

    platform = _platform_key()
    if platform == "win32":
        _windows_open_folder(folder)
        return
    if platform == "darwin":
        _macos_open_folder(folder)
        return

    _linux_open_path(folder)


def open_file_with_default_app(file_path: str | Path) -> None:
    """Open ``file_path`` with its registered default application."""
    path = _resolve_path(file_path)
    if not path.is_file():
        raise DesktopOpenError("File non trovato")

    platform = _platform_key()
    if platform == "win32":
        _windows_open_default_app(path)
        return
    if platform == "darwin":
        _macos_open_file_with_default_app(path)
        return

    _linux_open_path(path)


def open_folder_for_file(file_path: str | Path) -> None:
    """Open the folder containing ``file_path``, selecting it when possible."""
    open_file_in_explorer(file_path)


def open_folder_in_file_manager(folder_path: str | Path, file_path: str | Path | None = None) -> None:
    """Backward-compatible helper used by older call sites."""
    if file_path is not None:
        open_file_in_explorer(file_path)
        return
    open_folder_in_explorer(folder_path)
