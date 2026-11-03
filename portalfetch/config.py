"""Lettura della configurazione YAML e delle credenziali (mai nel file: solo variabili d'ambiente)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError


@dataclass
class Config:
    download_dir: Path
    tracking_file: Path
    browser: str = "chromium"
    headless: bool = True
    sites: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_config(path: Path) -> Config:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        raise ConfigError(f"file di configurazione non trovato: {path}") from None
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML non valido in {path}: {exc}") from exc

    sites = raw.get("sites")
    if not isinstance(sites, dict) or not sites:
        raise ConfigError("la configurazione deve avere almeno un sito sotto 'sites:'")
    for name, block in sites.items():
        if not isinstance(block, dict) or "type" not in block:
            raise ConfigError(f"sito {name!r}: manca il campo 'type'")

    base = path.parent  # i percorsi relativi partono dal file di configurazione
    return Config(
        download_dir=(base / raw.get("download_dir", "downloads")).resolve(),
        tracking_file=(base / raw.get("tracking_file", "state/tracking.json")).resolve(),
        browser=str(raw.get("browser", "chromium")),
        headless=bool(raw.get("headless", True)),
        sites=sites,
    )


def credentials_for(site: str) -> tuple[str, str]:
    """PORTALFETCH_<SITO>_USER / PORTALFETCH_<SITO>_PASSWORD."""
    key = "PORTALFETCH_" + "".join(c if c.isalnum() else "_" for c in site.upper())
    user, password = os.environ.get(f"{key}_USER"), os.environ.get(f"{key}_PASSWORD")
    if not user or not password:
        raise ConfigError(f"credenziali mancanti: imposta {key}_USER e {key}_PASSWORD")
    return user, password
