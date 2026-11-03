"""Registro dei documenti gia scaricati, scritto in modo atomico."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any) -> None:
    """Scrive su file temporaneo e poi sostituisce: un crash non lascia un JSON a meta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)  # atomico su Linux e Windows
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Tracking:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, list[str]] = {}
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # file corrotto: lo teniamo da parte invece di perderlo
                path.replace(path.with_suffix(".corrotto"))

    def is_done(self, site: str, doc_id: str) -> bool:
        return doc_id in self._data.get(site, [])

    def mark_done(self, site: str, doc_id: str) -> None:
        self._data.setdefault(site, []).append(doc_id)
        atomic_write_json(self.path, self._data)
