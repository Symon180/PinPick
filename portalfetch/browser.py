"""Scelta del browser, uguale su Linux e Windows."""
from __future__ import annotations

import os
from pathlib import Path


def find_edge() -> Path | None:
    """Edge e gia presente su Windows: evita di scaricare Chromium (~150 MB)."""
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(variable)
        if base:
            candidate = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidate.is_file():
                return candidate
    return None


def channel_for(choice: str | None) -> str | None:
    """None = Chromium di Playwright. 'auto' usa Edge se c'e. Valori ignoti -> Chromium."""
    choice = (choice or "chromium").strip().lower()
    if choice == "msedge" or (choice == "auto" and find_edge() is not None):
        return "msedge"
    return None
