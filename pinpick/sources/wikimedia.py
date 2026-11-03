"""Client dell'API di Wikimedia Commons: milioni di immagini libere, senza chiave.

Le licenze (CC, pubblico dominio) quasi sempre chiedono di citare l'autore: il programma
stampa autore, licenza e pagina del file. Si scarica la versione ridimensionata a 1280 px.
Documentazione: https://www.mediawiki.org/wiki/API:Search
"""
from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator

from ..errors import ApiError
from ..models import Photo

DEFAULT_BASE = "https://commons.wikimedia.org"
PER_PAGE = 50  # massimo per client anonimi
PAGES = 3
TIMEOUT_S = 30
USER_AGENT = "PinPick/0.1 (https://github.com/Symon180/PinPick; foto casuali da riga di comando)"
OK_MIME = {"image/jpeg", "image/png", "image/webp"}


class WikimediaSource:
    handles_search = True  # keyword e orientamento sono applicati qui, dentro photos()

    def __init__(self, base_url: str = DEFAULT_BASE):
        self.base_url = base_url.rstrip("/")

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{self.base_url}/w/api.php?{query}", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ApiError(f"Wikimedia Commons ha risposto HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ApiError(f"impossibile leggere Wikimedia Commons: {exc}") from exc
        if "error" in data:
            raise ApiError(f"Wikimedia Commons: {data['error'].get('info', 'errore')}")
        return data

    def photos(self, keyword: str = "", orientation: str = "any") -> Iterator[Photo]:
        keyword = keyword.strip()
        if not keyword:
            raise ApiError("Wikimedia Commons richiede una parola chiave (usa -k)")
        offset = 0
        for _ in range(PAGES):
            data = self._get({
                "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                "gsrsearch": f"{keyword} filetype:bitmap", "gsrlimit": PER_PAGE, "gsroffset": offset,
                "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280,
            })
            for page in (data.get("query") or {}).get("pages", {}).values():
                photo = parse_page(page)
                if photo and orientation in ("any", photo.orientation):
                    yield photo
            nxt = (data.get("continue") or {}).get("gsroffset")
            if nxt is None:
                return
            offset = int(nxt)


def _plain(value: Any) -> str:
    """extmetadata contiene HTML (es. link nell'autore): si toglie e si decodifica."""
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()


def parse_page(page: dict[str, Any]) -> Photo | None:
    info = (page.get("imageinfo") or [None])[0]
    if not info or info.get("mime") not in OK_MIME:
        return None
    url = info.get("thumburl") or info.get("url")
    if not url:
        return None
    meta = info.get("extmetadata") or {}
    width = int(info.get("thumbwidth") or info.get("width") or 0)
    height = int(info.get("thumbheight") or info.get("height") or 0)
    title = re.sub(r"^File:|\.[A-Za-z]+$", "", page.get("title", "")).strip()
    author = _plain((meta.get("Artist") or {}).get("value")) or "autore sconosciuto"
    licence = _plain((meta.get("LicenseShortName") or {}).get("value")) or "licenza non indicata"
    return Photo(
        id=f"commons-{page['pageid']}",
        title=title,
        description="",
        url=url,
        width=width,
        height=height,
        board="Wikimedia Commons",
        credit=f"{author} - {licence} - {info.get('descriptionurl', '')}",
    )
