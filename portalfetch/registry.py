"""Registro dei plugin: ogni portale si registra con un decorator."""
from __future__ import annotations

from typing import Callable, Type

from .base import Portal
from .errors import ConfigError

_REGISTRY: dict[str, Type[Portal]] = {}


def register(kind: str) -> Callable[[Type[Portal]], Type[Portal]]:
    def deco(cls: Type[Portal]) -> Type[Portal]:
        _REGISTRY[kind] = cls
        return cls

    return deco


def get_portal_class(kind: str) -> Type[Portal]:
    # import ritardato: carica i plugin integrati solo quando servono
    from . import portals  # noqa: F401

    try:
        return _REGISTRY[kind]
    except KeyError:
        raise ConfigError(f"tipo di portale sconosciuto: {kind!r} (disponibili: {sorted(_REGISTRY)})") from None
