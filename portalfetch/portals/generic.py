"""Portale 'generic': si descrive solo con i selettori CSS nel file YAML, senza scrivere codice."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from ..base import Document, Portal
from ..errors import AuthenticationRequired, ConfigError, PortalUnavailable
from ..registry import register

TIMEOUT_MS = 15_000
REQUIRED = ("user", "password", "submit", "logged_in", "links")


def safe_name(text: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    return cleaned or "documento"


@register("generic")
class GenericPortal(Portal):
    def __init__(self, name, settings):
        super().__init__(name, settings)
        sel = settings.get("selectors") or {}
        missing = [k for k in REQUIRED if k not in sel]
        if "url" not in settings or missing:
            raise ConfigError(f"sito {name!r}: servono 'url' e i selettori {list(REQUIRED)} (mancano: {missing})")
        self.sel = sel

    async def login(self, page: Page, user: str, password: str) -> None:
        try:
            await page.goto(self.settings["url"], timeout=TIMEOUT_MS)
        except Exception as exc:
            raise PortalUnavailable(f"{self.settings['url']} non raggiungibile: {exc}") from exc
        try:
            await page.locator(self.sel["user"]).fill(user, timeout=TIMEOUT_MS)
        except PlaywrightTimeout as exc:
            raise PortalUnavailable("form di login non trovato: la pagina e cambiata?") from exc
        await page.locator(self.sel["password"]).fill(password)
        await page.locator(self.sel["submit"]).click()
        try:
            await page.locator(self.sel["logged_in"]).first.wait_for(timeout=TIMEOUT_MS)
        except PlaywrightTimeout as exc:
            if "error" in self.sel and await page.locator(self.sel["error"]).count():
                raise AuthenticationRequired("credenziali rifiutate dal sito") from exc
            raise PortalUnavailable("dopo il login non compare ne l'area riservata ne un errore") from exc

    async def list_documents(self, page: Page) -> list[Document]:
        if "list_url" in self.settings:
            await page.goto(urljoin(page.url, self.settings["list_url"]), timeout=TIMEOUT_MS)
        docs: dict[str, Document] = {}
        for _ in range(int(self.settings.get("max_pages", 20))):
            for link in await page.locator(self.sel["links"]).all():
                href = await link.get_attribute("href")
                if not href:
                    continue
                url = urljoin(page.url, href)
                label = (await link.inner_text()).strip() or url
                docs.setdefault(url, Document(id=url, label=label, url=url))
            nxt = self.sel.get("next")
            if not nxt or not await page.locator(nxt).count():
                break
            await page.locator(nxt).first.click()
            await page.wait_for_load_state("domcontentloaded")
        return list(docs.values())

    async def download(self, page: Page, doc: Document, dest: Path) -> Path:
        response = await page.context.request.get(doc.url)
        if not response.ok:
            raise PortalUnavailable(f"download di {doc.label!r} fallito (HTTP {response.status})")
        ext = Path(doc.url.split("?")[0]).suffix or ".bin"
        target = dest / (safe_name(doc.label) + ("" if safe_name(doc.label).lower().endswith(ext.lower()) else ext))
        dest.mkdir(parents=True, exist_ok=True)
        target.write_bytes(await response.body())
        return target
