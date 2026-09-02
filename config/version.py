"""Versione applicazione — unica fonte: file VERSION nella root del progetto."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_VERSION_FILE = _ROOT / "VERSION"


def read_version() -> str:
    try:
        line = _VERSION_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        return line or "0.0.0-dev"
    except OSError:
        return "0.0.0-dev"


VERSION = read_version()
