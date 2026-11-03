"""Client dell'API ufficiale Pinterest v5 (solo libreria standard, nessuna dipendenza).

Legge le bacheche e i pin dell'utente a cui appartiene il token. Non fa scraping.
Documentazione: https://developers.pinterest.com/docs/api/v5/
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

from ..errors import ApiError, AuthError
from ..models import Photo

DEFAULT_BASE = "https://api.pinterest.com"
PAGE_SIZE = 100
MAX_PAGES = 50  # tetto di sicurezza contro paginazioni infinite
TIMEOUT_S = 20


class PinterestSource:
    def __init__(self, token: str, base_url: str = DEFAULT_BASE):
        self.token = token
        self.base_url = base_url.rstrip("/")

    # -- HTTP -------------------------------------------------------------
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        req = urllib.request.Request(
            f"{self.base_url}{path}" + (f"?{query}" if query else ""),
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise AuthError("token Pinterest rifiutato o scaduto: generane uno nuovo") from exc
            if exc.code == 429:
                raise ApiError("limite di richieste Pinterest superato: riprova tra qualche minuto") from exc
            raise ApiError(f"Pinterest ha risposto HTTP {exc.code} su {path}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError(f"impossibile leggere {path}: {exc}") from exc

    def _paged(self, path: str) -> Iterator[dict[str, Any]]:
        bookmark = None
        for _ in range(MAX_PAGES):
            data = self._get(path, {"page_size": PAGE_SIZE, "bookmark": bookmark})
            yield from data.get("items", [])
            bookmark = data.get("bookmark")
            if not bookmark:
                return

    # -- Foto -------------------------------------------------------------
    def photos(self) -> Iterator[Photo]:
        for board in self._paged("/v5/boards"):
            for pin in self._paged(f"/v5/boards/{board['id']}/pins"):
                photo = parse_pin(pin, board.get("name", ""))
                if photo:
                    yield photo


def parse_pin(pin: dict[str, Any], board_name: str = "") -> Photo | None:
    """Trasforma un pin in Photo. Ignora video e pin senza immagine."""
    media = pin.get("media") or {}
    if media.get("media_type", "image") != "image":
        return None
    images = media.get("images") or {}
    best = images.get("originals") or max(
        images.values(), key=lambda i: i.get("width", 0) * i.get("height", 0), default=None
    )
    if not best or not best.get("url"):
        return None
    return Photo(
        id=str(pin["id"]),
        title=pin.get("title") or "",
        description=pin.get("description") or "",
        url=best["url"],
        width=int(best.get("width") or 0),
        height=int(best.get("height") or 0),
        board=board_name,
    )
