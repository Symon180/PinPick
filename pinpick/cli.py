"""Riga di comando. Le informazioni mancanti vengono chieste all'utente."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .downloader import History, download
from .errors import EXIT_NO_RESULTS, EXIT_OK, ConfigError, PinPickError
from .models import ORIENTATIONS
from .picker import select
from .sources import openverse, pexels, pinterest, wikimedia

SOURCES = ("wikimedia", "openverse", "pexels", "pinterest")


def ask(prompt: str, default: str) -> str:
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or default


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pinpick", description="Scarica foto a caso da Pinterest (tue bacheche) o Pexels.")
    p.add_argument("--source", "-s", choices=SOURCES, default="wikimedia",
                   help="wikimedia e openverse = immagini libere (nessuna chiave, default: wikimedia); "
                        "pexels = catalogo (chiave); pinterest = le tue bacheche (token)")
    p.add_argument("--keyword", "-k", help="parola chiave")
    p.add_argument("--orientation", "-o", choices=ORIENTATIONS, help="orientamento della foto")
    p.add_argument("--count", "-n", type=int, help="quante foto scaricare")
    p.add_argument("--out", type=Path, default=Path("foto"), help="cartella di destinazione (default: ./foto)")
    p.add_argument("--allow-repeats", action="store_true", help="puo riscaricare foto gia scaricate")
    return p


def make_source(name: str):
    """Crea la fonte leggendo le credenziali dall'ambiente (mai da file o riga di comando)."""
    base = os.environ.get("PINPICK_API_BASE")
    if name == "wikimedia":
        return wikimedia.WikimediaSource(base or wikimedia.DEFAULT_BASE)
    if name == "openverse":
        return openverse.OpenverseSource(base or openverse.DEFAULT_BASE)
    if name == "pexels":
        key = os.environ.get("PEXELS_API_KEY")
        if not key:
            raise ConfigError("manca la chiave: imposta PEXELS_API_KEY (gratuita su pexels.com/api)")
        return pexels.PexelsSource(key, base or pexels.DEFAULT_BASE)
    token = os.environ.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        raise ConfigError("manca il token: imposta PINTEREST_ACCESS_TOKEN (vedi README, sezione Token)")
    return pinterest.PinterestSource(token, base or pinterest.DEFAULT_BASE)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if sys.stdin.isatty():  # chiede solo cio che manca
        if not args.keyword:
            args.keyword = ask("Parola chiave (es. mountain, cat, cyberpunk)", "nature")
        if args.orientation is None:
            args.orientation = ask(f"Orientamento ({'/'.join(ORIENTATIONS)})", "any")
        if args.count is None:
            args.count = int(ask("Quante foto", "1"))
    keyword, orientation, count = args.keyword or "", args.orientation or "any", args.count or 1

    try:
        source = make_source(args.source)
        history = History(args.out / ".scaricate.json")
        if source.handles_search:  # il server ha gia filtrato: non rifiltrare per testo
            candidates = source.photos(keyword, orientation)
            chosen = select(candidates, "", "any", count,  # orientamento gia filtrato dal server
                            exclude_ids=set() if args.allow_repeats else history.ids)
        else:
            chosen = select(source.photos(), keyword, orientation, count,
                            exclude_ids=set() if args.allow_repeats else history.ids)
        if not chosen:
            print("Nessuna foto trovata con questi criteri (o le hai gia scaricate tutte).")
            return EXIT_NO_RESULTS
        for photo in chosen:
            path = download(photo, args.out)
            history.add(photo.id)
            print(f"Scaricata: {path}  [{photo.board} | {photo.orientation} {photo.width}x{photo.height}]")
            if photo.credit:
                print(f"   Credito: {photo.credit}")
        return EXIT_OK
    except PinPickError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
