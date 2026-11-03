"""Download sicuro dell'immagine e memoria delle foto gia scaricate."""
from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .errors import ApiError
from .models import Photo

MAX_BYTES = 25 * 1024 * 1024
TIMEOUT_S = 30
EXT_BY_TYPE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def safe_filename(text: str) -> str:
    """Toglie i caratteri vietati su Windows e impedisce path traversal."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    return cleaned[:80] or "foto"


def download(photo: Photo, dest_dir: Path) -> Path:
    req = urllib.request.Request(photo.url, headers={"User-Agent": "PinPick/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            ctype = resp.headers.get_content_type()
            if ctype not in EXT_BY_TYPE:
                raise ApiError(f"il pin {photo.id} non punta a un'immagine ({ctype})")
            body = resp.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ApiError(f"download del pin {photo.id} fallito: {exc}") from exc
    if len(body) > MAX_BYTES:
        raise ApiError(f"il pin {photo.id} supera {MAX_BYTES // 1024 // 1024} MB")
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = safe_filename(f"{photo.title or 'pin'}-{photo.id}") + EXT_BY_TYPE[ctype]
    target = dest_dir / name
    target.write_bytes(body)
    return target


class History:
    """Elenco degli id gia scaricati, scritto in modo atomico (un crash non lo corrompe)."""

    def __init__(self, path: Path):
        self.path = path
        self.ids: set[str] = set()
        if path.exists():
            try:
                self.ids = set(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, TypeError):
                path.replace(path.with_suffix(".corrotto"))  # lo teniamo da parte

    def add(self, photo_id: str) -> None:
        self.ids.add(photo_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(sorted(self.ids), fh)
            os.replace(tmp, self.path)  # atomico su Linux e Windows
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
