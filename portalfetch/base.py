"""Contratto che ogni portale (plugin) deve rispettare."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import Page


@dataclass(frozen=True)
class Document:
    """Un documento scaricabile (es. una fattura)."""

    id: str
    label: str
    url: str


class Portal(ABC):
    """Un sito da cui scaricare documenti.

    `settings` e il blocco del sito nel file di configurazione.
    Il motore chiama sempre `logout` in un `finally`: non deve sollevare.
    """

    def __init__(self, name: str, settings: dict[str, Any]):
        self.name = name
        self.settings = settings

    @abstractmethod
    async def login(self, page: Page, user: str, password: str) -> None: ...

    @abstractmethod
    async def list_documents(self, page: Page) -> list[Document]: ...

    @abstractmethod
    async def download(self, page: Page, doc: Document, dest: Path) -> Path: ...

    async def logout(self, page: Page) -> None:  # opzionale
        return None
