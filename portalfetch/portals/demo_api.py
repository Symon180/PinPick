"""Plugin in codice: stesso login del portale generico, ma elenco preso da un'API JSON.

Mostra come si scrive un portale 'a mano' quando i selettori CSS non bastano.
"""
from __future__ import annotations

from urllib.parse import urljoin

from playwright.async_api import Page

from ..base import Document
from ..errors import PortalUnavailable
from ..registry import register
from .generic import GenericPortal


@register("demo_api")
class DemoApiPortal(GenericPortal):
    async def list_documents(self, page: Page) -> list[Document]:
        response = await page.context.request.get(urljoin(page.url, self.settings.get("api_path", "/api/invoices")))
        if not response.ok:
            raise PortalUnavailable(f"API fatture non disponibile (HTTP {response.status})")
        return [
            Document(id=str(item["id"]), label=item["number"], url=urljoin(page.url, item["pdf"]))
            for item in await response.json()
        ]
