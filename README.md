# PinPick

[![CI](https://github.com/Symon180/PinPick/actions/workflows/ci.yml/badge.svg)](https://github.com/Symon180/PinPick/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/Dipendenze%20runtime-0-brightgreen)
![Platform](https://img.shields.io/badge/Linux%20%7C%20Windows-tested%20in%20CI-lightgrey)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

Programma a riga di comando che **scarica foto a caso dalle tue bacheche Pinterest**, in base a quello che chiedi:
parola chiave, orientamento (verticale/orizzontale/quadrata) e quante foto.

Usa l'**API ufficiale di Pinterest v5**, senza scraping né browser automatici: legge i pin dell'account a cui appartiene il tuo token.
Python puro, **nessuna dipendenza** da installare per usarlo.

*English: a CLI that downloads random photos from your own Pinterest boards through the official v5 API, filtered by keyword, orientation and count. Standard library only. Tested on Linux and Windows in CI.*

## Uso
```bash
pip install -e .
export PINTEREST_ACCESS_TOKEN=...        # Windows PowerShell: $env:PINTEREST_ACCESS_TOKEN="..."
pinpick                                  # chiede parola chiave, orientamento e quantita
pinpick -k mare -o landscape -n 3        # oppure tutto da riga di comando
```
Le foto finiscono in `./foto/`. PinPick ricorda quelle già scaricate (`foto/.scaricate.json`) e non le ripete, a meno di usare `--allow-repeats`.

| Opzione | Significato |
|---|---|
| `-k, --keyword` | cerca in titolo, descrizione e nome della bacheca (senza maiuscole) |
| `-o, --orientation` | `any`, `portrait`, `landscape`, `square` |
| `-n, --count` | quante foto scaricare (default 1) |
| `--out` | cartella di destinazione |
| `--allow-repeats` | permette di riscaricare foto già prese |

Codici di uscita: `0` ok, `1` nessuna foto trovata, `2` token/configurazione, `3` errore dell'API.

## Token
Serve un token personale dell'API Pinterest (non c'è alcun login con password nel programma):
1. Crea un'app su [developers.pinterest.com](https://developers.pinterest.com/apps/).
2. Genera un access token con gli scope `boards:read` e `pins:read`.
3. Esportalo come `PINTEREST_ACCESS_TOKEN`. Non va mai scritto nel codice né committato (`.env` è nel `.gitignore`).

L'API permette di leggere **i tuoi** pin e le tue bacheche, non di cercare liberamente in tutto Pinterest. L'accesso alle API può richiedere l'approvazione di Pinterest: controlla le condizioni attuali sul loro sito.

## Provarlo senza token
Il progetto include una **finta API Pinterest** locale con 2 bacheche e 8 foto generate al volo:
```bash
pip install -e ".[dev]"
python -m fake_pinterest                                  # terminale 1: http://127.0.0.1:8766
# terminale 2:
export PINPICK_API_BASE=http://127.0.0.1:8766 PINTEREST_ACCESS_TOKEN=demo-token
pinpick -k spiaggia -o portrait
```
La finta API serve anche ai test, che quindi girano ovunque senza rete.

## Architettura
```
pinpick/
├── sources/pinterest.py   # client API v5: paginazione, errori 401/429, solo immagini
├── models.py              # Photo (orientamento, ricerca per parola chiave)
├── picker.py              # filtri + scelta casuale (riproducibile nei test)
├── downloader.py          # download sicuro (tipo e peso verificati, nome file ripulito) + storico atomico
├── cli.py                 # domande interattive e opzioni
└── errors.py              # AuthError / ApiError / ConfigError con codici di uscita
fake_pinterest/            # finta API per demo e test
tests/                     # 16 test: unitari ed end-to-end
```
Scelte progettuali: nessuna dipendenza esterna; `pinpick/sources/` è pensato per aggiungere altre fonti (es. Unsplash); storico scritto in modo atomico; limite di 25 MB e controllo del content-type sui download; tetto alle pagine lette.

## Test
```bash
pytest
```

## Licenza
MIT, autore [Simone Mariotti](https://github.com/Symon180). Rispetta i diritti d'autore delle immagini che scarichi.
