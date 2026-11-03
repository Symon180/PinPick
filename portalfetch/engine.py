"""Il motore: per ogni sito login -> elenco -> scarica i nuovi -> logout."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import async_playwright

from .browser import channel_for
from .config import Config, credentials_for
from .errors import (EXIT_OK, EXIT_PARTIAL, AuthenticationRequired, ConfigError,
                     PortalError)
from .registry import get_portal_class
from .tracking import Tracking


@dataclass
class SiteResult:
    site: str
    downloaded: list[str] = field(default_factory=list)
    skipped: int = 0
    error: str | None = None


def safe_filename(text: str) -> str:
    """Toglie i caratteri non ammessi su Windows e blocca path traversal ('../')."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    return cleaned or "documento"


async def run(config: Config, only: list[str] | None = None, scan_only: bool = False) -> list[SiteResult]:
    names = only or list(config.sites)
    unknown = [n for n in names if n not in config.sites]
    if unknown:
        raise ConfigError(f"siti non presenti in configurazione: {unknown}")

    tracking = Tracking(config.tracking_file)
    results: list[SiteResult] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=config.headless, channel=channel_for(config.browser))
        try:
            for name in names:
                results.append(await _run_site(browser, config, name, tracking, scan_only))
        finally:
            await browser.close()
    return results


async def _run_site(browser, config: Config, name: str, tracking: Tracking, scan_only: bool) -> SiteResult:
    result = SiteResult(site=name)
    block = config.sites[name]
    context = await browser.new_context(accept_downloads=True)
    page = await context.new_page()
    portal = None
    try:
        portal = get_portal_class(block["type"])(name, block)
        user, password = credentials_for(name)
        await portal.login(page, user, password)  # un solo tentativo
        docs = await portal.list_documents(page)
        dest_dir = config.download_dir / safe_filename(name)
        for doc in docs:
            if tracking.is_done(name, doc.id):
                result.skipped += 1
                continue
            if scan_only:
                result.downloaded.append(f"(da scaricare) {doc.label}")
                continue
            saved = await portal.download(page, doc, dest_dir)
            tracking.mark_done(name, doc.id)  # solo dopo il salvataggio riuscito
            result.downloaded.append(saved.name)
    except AuthenticationRequired as exc:
        result.error = f"accesso rifiutato: {exc}"
    except PortalError as exc:
        result.error = str(exc)
    except Exception as exc:  # un sito guasto non ferma gli altri
        result.error = f"errore imprevisto ({type(exc).__name__}): {exc}"
    finally:
        if portal is not None:
            try:
                await portal.logout(page)
            except Exception:
                pass
        await context.close()
    return result


def exit_code(results: list[SiteResult]) -> int:
    return EXIT_PARTIAL if any(r.error for r in results) else EXIT_OK
