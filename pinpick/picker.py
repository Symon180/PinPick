"""Filtri e scelta casuale delle foto."""
from __future__ import annotations

import random
from typing import Iterable

from .errors import ConfigError
from .models import ORIENTATIONS, Photo


def select(
    photos: Iterable[Photo],
    keyword: str = "",
    orientation: str = "any",
    count: int = 1,
    exclude_ids: set[str] | frozenset[str] = frozenset(),
    rng: random.Random | None = None,
) -> list[Photo]:
    """Filtra per parola chiave e orientamento, scarta le gia scaricate, ne sceglie `count` a caso."""
    if orientation not in ORIENTATIONS:
        raise ConfigError(f"orientamento non valido: {orientation!r} (scegli tra {', '.join(ORIENTATIONS)})")
    if count < 1:
        raise ConfigError("il numero di foto deve essere almeno 1")
    candidates = [
        p
        for p in photos
        if p.id not in exclude_ids and p.matches(keyword) and orientation in ("any", p.orientation)
    ]
    return (rng or random).sample(candidates, min(count, len(candidates)))
