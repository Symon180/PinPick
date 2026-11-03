"""Client dell'API Openverse: immagini con licenze libere (Creative Commons), senza chiave.

L'accesso anonimo ha limiti bassi ma basta per uso personale. Le licenze richiedono quasi sempre
di citare l'autore: il programma stampa il credito con licenza e link.
Documentazione: https://api.openverse.org/v1/
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

from ..errors import ApiError
from ..models import Photo

DEFAULT_BASE = "https://api.openverse.org"
PER_PAGE = 20  # massimo consentito agli anonimi
PAGES = 3
TIMEOUT_S = 45
ATTEMPTS = 3
RETRY_PAUSE_S = 1.0
ASPECT = {"portrait": "tall", "landscape": "wide", "square": "square"}


class OpenverseSource:
    handles_search = True  # keyword e orientamento sono gia applicati dal server

    def __init__(self, base_url: str = DEFAULT_BASE):
        self.base_url = base_url.rstrip("/")

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
        req = urllib.request.Request(f"{self.base_url}/v1/images/?{query}", headers={"User-Agent": "PinPick/0.1"})
        last: Exception | None = None
        for attempt in range(ATTEMPTS):  # il servizio anonimo a volte risponde 5xx o e lentissimo
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    raise ApiError("limite di richieste Openverse superato: riprova tra qualche minuto") from exc
                if exc.code < 500:
                    raise ApiError(f"Openverse ha risposto HTTP {exc.code}") from exc
                last = exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = exc
            time.sleep(RETRY_PAUSE_S * (attempt + 1))
        raise ApiError(f"Openverse non risponde dopo {ATTEMPTS} tentativi ({last}): e un problema del servizio, riprova piu tardi")

    def photos(self, keyword: str = "", orientation: str = "any") -> Iterator[Photo]:
        keyword = keyword.strip()
        if not keyword:
            raise ApiError("Openverse richiede una parola chiave (usa -k)")
        for page in range(1, PAGES + 1):
            data = self._get({
                "q": keyword, "aspect_ratio": ASPECT.get(orientation),
                "page_size": PER_PAGE, "page": page, "mature": "false",
            })
            for item in data.get("results", []):
                photo = parse_image(item)
                if photo:
                    yield photo
            if page >= int(data.get("page_count") or 0):
                return


def parse_image(item: dict[str, Any]) -> Photo | None:
    if not item.get("url") or not item.get("id"):
        return None
    lic = f"CC {str(item.get('license', '')).upper()} {item.get('license_version', '')}".strip()
    return Photo(
        id=f"openverse-{item['id']}",
        title=item.get("title") or "",
        description="",
        url=item["url"],
        width=int(item.get("width") or 0),
        height=int(item.get("height") or 0),
        board=str(item.get("source") or "Openverse"),
        credit=f"{item.get('creator') or 'autore sconosciuto'} - {lic} - {item.get('foreign_landing_url', '')}",
    )
