#!/usr/bin/env python3
"""Selettore cartelle Windows per helper Securtek (nessuna console PowerShell)."""

from __future__ import annotations

import sys
from pathlib import Path


def pick_folder(title: str = "Seleziona cartella pratica") -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        root.lift()
        root.focus_force()
    except tk.TclError:
        pass

    selected = filedialog.askdirectory(title=title, mustexist=True, parent=root)
    root.destroy()
    if not selected:
        return None
    return str(Path(selected))


def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "Seleziona cartella pratica"
    selected = pick_folder(title)
    if selected:
        print(selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
