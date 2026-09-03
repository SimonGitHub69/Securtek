#!/usr/bin/env python3
"""Selettore cartelle Windows nativo (Shell32, nessuna console PowerShell/tkinter)."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

BIF_RETURNONLYFSDIRS = 0x00000001
BIF_NEWDIALOGSTYLE = 0x00000040
BIF_NONEWFOLDERBUTTON = 0x00000200


class BROWSEINFO(ctypes.Structure):
    _fields_ = [
        ("hwndOwner", wintypes.HWND),
        ("pidlRoot", ctypes.c_void_p),
        ("pszDisplayName", wintypes.LPWSTR),
        ("lpszTitle", wintypes.LPCWSTR),
        ("ulFlags", wintypes.UINT),
        ("lpfn", ctypes.c_void_p),
        ("lParam", wintypes.LPARAM),
        ("iImage", ctypes.c_int),
    ]


def pick_folder(title: str = "Seleziona cartella pratica") -> str | None:
    ole32 = ctypes.windll.ole32
    shell32 = ctypes.windll.shell32
    user32 = ctypes.windll.user32

    ole32.CoInitializeEx(None, 0x2)

    display_name = ctypes.create_unicode_buffer(260)
    browse_info = BROWSEINFO()
    browse_info.hwndOwner = user32.GetForegroundWindow()
    browse_info.pszDisplayName = display_name
    browse_info.lpszTitle = title
    browse_info.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE | BIF_NONEWFOLDERBUTTON

    pidl = shell32.SHBrowseForFolderW(ctypes.byref(browse_info))
    if not pidl:
        ole32.CoUninitialize()
        return None

    path_buf = ctypes.create_unicode_buffer(260)
    if not shell32.SHGetPathFromIDListW(pidl, path_buf):
        ole32.CoTaskMemFree(pidl)
        ole32.CoUninitialize()
        return None

    ole32.CoTaskMemFree(pidl)
    ole32.CoUninitialize()
    selected = path_buf.value.strip()
    if not selected:
        return None
    return str(Path(selected))


def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "Seleziona cartella pratica"
    selected = pick_folder(title)
    if selected:
        print(selected, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
