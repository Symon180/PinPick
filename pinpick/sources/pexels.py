"""Client dell'API ufficiale Pexels (foto gratuite, ricerca su tutto il catalogo).

Serve una chiave gratuita: https://www.pexels.com/api/  ->  variabile PEXELS_API_KEY.
La ricerca (parola chiave e orientamento) la fa il server; qui si leggono poche pagine
e si lascia scegliere a caso a `picker.select`.
Condizioni d'uso: citare Pexels e il fotografo (il programma stampa il credito).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

from ..errors import ApiError, AuthError
from ..models import Photo

DEFAULT_BASE = "https://api.pexels.com"
PER_PAGE = 80
PAGES = 3  # 240 candidati bastano per una scelta casuale e restano ben sotto i limiti
TIMEOUT_S = 20
SERVER_ORIENTATION = {"portrait": "portrait", "landscape": "landscape", "square": "square"}


class PexelsSource:
    handles_search = True  # keyword e orientamento sono gia applicati dal server

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
        req = urllib.request.Request(
            f"{self.base_url}{path}?{query}", headers={"Authorization": self.api_key, "User-Agent": "PinPick/0.1"}
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise AuthError("chiave Pexels rifiutata: controlla PEXELS_API_KEY") from exc
            if exc.code == 429:
                raise ApiError("limite di richieste Pexels superato: riprova piu tardi") from exc
            raise ApiError(f"Pexels ha risposto HTTP {exc.code} su {path}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError(f"impossibile leggere {path}: {exc}") from exc

    def photos(self, keyword: str = "", orientation: str = "any") -> Iterator[Photo]:
        keyword = keyword.strip()
        path = "/v1/search" if keyword else "/v1/curated"  # senza parola chiave: selezione della redazione
        for page in range(1, PAGES + 1):
            data = self._get(path, {
                "query": keyword, "orientation": SERVER_ORIENTATION.get(orientation),
                "per_page": PER_PAGE, "page": page,
            })
            for item in data.get("photos", []):
                photo = parse_photo(item)
                if photo:
                    yield photo
            if not data.get("next_page"):
                return


def parse_photo(item: dict[str, Any]) -> Photo | None:
    src = item.get("src") or {}
    url = src.get("large2x") or src.get("large") or src.get("original")
    if not url or "id" not in item:
        return None
    return Photo(
        id=f"pexels-{item['id']}",
        title=item.get("alt") or "",
        description="",
        url=url,
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        board="Pexels",
        credit=f"{item.get('photographer', 'sconosciuto')} (Pexels) {item.get('url', '')}".strip(),
    )
