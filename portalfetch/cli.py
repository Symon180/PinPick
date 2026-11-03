"""Interfaccia a riga di comando: `python -m portalfetch run --config sites.yaml`."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .config import load_config
from .engine import exit_code, run
from .errors import EXIT_CONFIG, ConfigError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="portalfetch", description="Scarica documenti da portali web configurabili.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="esegue i download")
    p_run.add_argument("--config", type=Path, default=Path("sites.yaml"))
    p_run.add_argument("--site", action="append", help="solo questo sito (ripetibile)")
    p_run.add_argument("--scan-only", action="store_true", help="elenca senza scaricare")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        results = asyncio.run(run(config, only=args.site, scan_only=args.scan_only))
    except ConfigError as exc:
        print(f"Errore di configurazione: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    for r in results:
        status = f"ERRORE: {r.error}" if r.error else f"ok, {len(r.downloaded)} nuovi, {r.skipped} gia scaricati"
        print(f"[{r.site}] {status}")
        for name in r.downloaded:
            print(f"   - {name}")
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
