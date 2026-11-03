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
from .sources.pinterest import DEFAULT_BASE, PinterestSource


def ask(prompt: str, default: str) -> str:
    answer = input(f"{prompt} [{default}]: ").strip()
    return answer or default


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pinpick", description="Scarica foto a caso dalle tue bacheche Pinterest.")
    p.add_argument("--keyword", "-k", help="parola chiave (titolo, descrizione o nome bacheca)")
    p.add_argument("--orientation", "-o", choices=ORIENTATIONS, help="orientamento della foto")
    p.add_argument("--count", "-n", type=int, help="quante foto scaricare")
    p.add_argument("--out", type=Path, default=Path("foto"), help="cartella di destinazione (default: ./foto)")
    p.add_argument("--allow-repeats", action="store_true", help="puo riscaricare foto gia scaricate")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    interactive = sys.stdin.isatty()
    if interactive:  # chiede solo cio che manca
        if args.keyword is None:
            args.keyword = ask("Parola chiave (vuoto = qualsiasi)", "")
        if args.orientation is None:
            args.orientation = ask(f"Orientamento ({'/'.join(ORIENTATIONS)})", "any")
        if args.count is None:
            args.count = int(ask("Quante foto", "1"))
    keyword, orientation, count = args.keyword or "", args.orientation or "any", args.count or 1

    try:
        token = os.environ.get("PINTEREST_ACCESS_TOKEN")
        if not token:
            raise ConfigError(
                "manca il token: imposta la variabile PINTEREST_ACCESS_TOKEN (vedi README, sezione Token)"
            )
        source = PinterestSource(token, os.environ.get("PINPICK_API_BASE", DEFAULT_BASE))
        history = History(args.out / ".scaricate.json")
        chosen = select(
            source.photos(), keyword, orientation, count,
            exclude_ids=set() if args.allow_repeats else history.ids,
        )
        if not chosen:
            print("Nessuna foto trovata con questi criteri (o le hai gia scaricate tutte).")
            return EXIT_NO_RESULTS
        for photo in chosen:
            path = download(photo, args.out)
            history.add(photo.id)
            print(f"Scaricata: {path}  [{photo.board} | {photo.orientation} {photo.width}x{photo.height}]")
        return EXIT_OK
    except PinPickError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
