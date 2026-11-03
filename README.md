# PortalFetch

[![CI](https://github.com/Symon180/PortalFetch/actions/workflows/ci.yml/badge.svg)](https://github.com/Symon180/PortalFetch/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Browser-Playwright-2EAD33?logo=playwright&logoColor=white)
![Platform](https://img.shields.io/badge/Linux%20%7C%20Windows-tested%20in%20CI-lightgrey)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

Motore a **plugin** in Python per scaricare in automatico documenti (es. fatture PDF) da portali web con login.
Nasce dall'esperienza di automazione di un back office che gestiva decine di portali diversi: qui la parte generica
(motore, tracking, gestione errori) è separata dai siti, che si aggiungono con un file di configurazione o con un piccolo plugin.

> Il progetto include un **portale demo** locale con fatture finte: si prova subito, senza account né siti reali.

*English: a plugin-based Playwright engine that logs in to web portals and downloads new documents, with idempotent tracking, safe file handling and a demo portal. Tested on Linux and Windows in CI.*

## Funzionalità
- **Due modi per aggiungere un sito:** solo selettori CSS in YAML (`type: generic`), oppure un plugin Python che estende `Portal` (vedi `portalfetch/portals/demo_api.py`).
- **Idempotente:** i documenti già scaricati vengono saltati (registro JSON scritto in modo atomico, anche se il programma si interrompe).
- **Errori distinti:** credenziali rifiutate, sito non disponibile, configurazione errata; un sito guasto non blocca gli altri; codici di uscita per scheduler.
- **Sicurezza:** credenziali solo da variabili d'ambiente, un solo tentativo di login (per non bloccare l'account), nomi file ripuliti contro path traversal.
- **Portabile:** Linux e Windows (su Windows può usare Edge già installato con `browser: msedge`).

## Avvio rapido
```bash
git clone https://github.com/Symon180/PortalFetch.git && cd PortalFetch
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
playwright install chromium

python -m demo_server &                                   # portale demo su http://127.0.0.1:8765
cp sites.example.yaml sites.yaml
export PORTALFETCH_DEMO_USER=demo PORTALFETCH_DEMO_PASSWORD=demo123    # Windows PowerShell: $env:NOME="valore"
python -m portalfetch run --config sites.yaml --site demo
```
I PDF finiscono in `downloads/demo/`; rilanciando il comando non viene scaricato nulla di nuovo. Opzioni: `--scan-only`, `--site` (ripetibile).

## Aggiungere un nuovo sito
1. Apri la pagina di login, trova i selettori CSS di utente, password, pulsante e dei link ai documenti.
2. Aggiungi un blocco sotto `sites:` in `sites.yaml` (vedi `sites.example.yaml`).
3. Imposta `PORTALFETCH_<NOME>_USER` e `PORTALFETCH_<NOME>_PASSWORD`.
4. Se il sito ha un flusso particolare, crea una classe con `@register("mio_tipo")` che implementa `login`, `list_documents` e `download`.

Usalo solo su account e dati tuoi e nel rispetto dei termini d'uso dei siti.

## Architettura
```
portalfetch/
├── engine.py      # per ogni sito: login -> elenco -> scarica i nuovi -> logout (sempre, in finally)
├── base.py        # contratto Portal / Document
├── registry.py    # @register("tipo")
├── portals/       # plugin: generic (CSS) e demo_api (codice)
├── tracking.py    # registro dei già scaricati, scrittura atomica
├── config.py      # YAML + credenziali da ambiente
├── browser.py     # Chromium o Edge
└── errors.py      # AuthenticationRequired / PortalUnavailable / ConfigError
demo_server/       # portale fittizio (Flask) per provare e testare
tests/             # unit test + end-to-end con browser reale
```

## Test
```bash
pytest
```
12 test: unitari (configurazione, tracking, sicurezza dei nomi file) ed end-to-end con browser reale contro il portale demo (paginazione, secondo giro senza duplicati, password errata, `--scan-only`). La CI li esegue su Ubuntu e Windows.

## Licenza
MIT, autore [Simone Mariotti](https://github.com/Symon180).
