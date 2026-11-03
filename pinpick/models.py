from __future__ import annotations

from dataclasses import dataclass

ORIENTATIONS = ("any", "portrait", "landscape", "square")


@dataclass(frozen=True)
class Photo:
    id: str
    title: str
    description: str
    url: str
    width: int
    height: int
    board: str = ""

    @property
    def orientation(self) -> str:
        if self.width == self.height:
            return "square"
        return "portrait" if self.height > self.width else "landscape"

    def matches(self, keyword: str) -> bool:
        """Parola chiave cercata in titolo, descrizione e nome bacheca, senza badare alle maiuscole."""
        needle = keyword.strip().lower()
        if not needle:
            return True
        return needle in f"{self.title} {self.description} {self.board}".lower()
