"""Finta API Pinterest v5 per provare e testare PinPick senza token ne rete.

Avvio:  python -m fake_pinterest     ->  http://127.0.0.1:8766   (token: demo-token)
Poi:    PINPICK_API_BASE=http://127.0.0.1:8766 PINTEREST_ACCESS_TOKEN=demo-token python -m pinpick
"""
from __future__ import annotations

import struct
import zlib

from flask import Flask, Response, jsonify, request

TOKEN = "demo-token"
PEXELS_KEY = "demo-key"
SERVER_PAGE = 4  # pagine piccole apposta: forza il client a usare la paginazione

BOARDS = [{"id": "b1", "name": "Viaggi"}, {"id": "b2", "name": "Cucina"}]
# (id, titolo, descrizione, larghezza, altezza, bacheca)
PINS = [
    ("p1", "Mare al tramonto", "spiaggia in Sardegna", 300, 200, "b1"),
    ("p2", "Montagne innevate", "Dolomiti d'inverno", 200, 300, "b1"),
    ("p3", "Citta di notte", "Tokyo luci", 300, 200, "b1"),
    ("p4", "Ponte antico", "Firenze", 240, 240, "b1"),
    ("p5", "Spiaggia deserta", "mare cristallino", 200, 300, "b1"),
    ("p6", "Pizza napoletana", "forno a legna", 300, 200, "b2"),
    ("p7", "Torta al cioccolato", "dolce", 200, 300, "b2"),
    ("p8", "Pasta fresca", "fatta in casa", 240, 240, "b2"),
]


def png(width: int, height: int, color=(70, 130, 180)) -> bytes:
    """PNG valido di un solo colore, generato a mano (solo zlib e struct)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    row = b"\x00" + bytes(color) * width
    raw = row * height
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _page(items: list, bookmark: str | None):
    start = int(bookmark or 0)
    chunk = items[start : start + SERVER_PAGE]
    nxt = str(start + SERVER_PAGE) if start + SERVER_PAGE < len(items) else None
    return jsonify(items=chunk, bookmark=nxt)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.before_request
    def auth():
        if request.path.startswith("/v5/") and request.headers.get("Authorization") != f"Bearer {TOKEN}":
            return jsonify(code=2, message="Authentication failed."), 401

    @app.get("/v5/boards")
    def boards():
        return _page(BOARDS, request.args.get("bookmark"))

    @app.get("/v5/boards/<board_id>/pins")
    def pins(board_id: str):
        base = request.host_url.rstrip("/")
        items = [
            {
                "id": pid, "title": title, "description": desc,
                "media": {"media_type": "image", "images": {
                    "150x150": {"url": f"{base}/img/{pid}.png?s=small", "width": 150, "height": 150},
                    "originals": {"url": f"{base}/img/{pid}.png", "width": w, "height": h},
                }},
            }
            for pid, title, desc, w, h, bid in PINS if bid == board_id
        ] + ([{"id": "v1", "title": "Video", "media": {"media_type": "video"}}] if board_id == "b1" else [])
        return _page(items, request.args.get("bookmark"))

    @app.get("/img/<pid>.png")
    def image(pid: str):
        for p, _t, _d, w, h, _b in PINS:
            if p == pid:
                return Response(png(w, h), mimetype="image/png")
        return Response("non trovato", 404)

    # --- finta API Pexels (chiave: demo-key) --------------------------------
    def pexels_search():
        if request.headers.get("Authorization") != PEXELS_KEY:
            return jsonify(error="Unauthorized"), 401
        query = request.args.get("query", "").lower()
        wanted = request.args.get("orientation")
        page = request.args.get("page", 1, type=int)
        base = request.host_url.rstrip("/")
        hits = [
            {"id": 1000 + i, "alt": title, "width": w, "height": h, "photographer": "Mario Rossi",
             "url": f"https://www.pexels.com/photo/{1000 + i}/",
             "src": {"large2x": f"{base}/img/{pid}.png"}}
            for i, (pid, title, desc, w, h, _b) in enumerate(PINS)
            if query in f"{title} {desc}".lower()
            and (not wanted or wanted == ("square" if w == h else "portrait" if h > w else "landscape"))
        ]
        chunk = hits[(page - 1) * SERVER_PAGE : page * SERVER_PAGE]
        more = page * SERVER_PAGE < len(hits)
        return jsonify(photos=chunk, next_page=f"{base}/v1/search?page={page + 1}" if more else None)

    app.add_url_rule("/v1/search", "pexels_search", pexels_search)
    app.add_url_rule("/v1/curated", "pexels_curated", pexels_search)

    # --- finta API Wikimedia Commons (nessuna chiave) -------------------------
    @app.get("/w/api.php")
    def wikimedia_api():
        query = request.args.get("gsrsearch", "").replace("filetype:bitmap", "").strip().lower()
        offset = request.args.get("gsroffset", 0, type=int)
        base = request.host_url.rstrip("/")
        hits = [
            (pid, title, w, h) for pid, title, desc, w, h, _b in PINS if query in f"{title} {desc}".lower()
        ]
        chunk = hits[offset : offset + SERVER_PAGE]
        pages = {
            str(500 + i): {
                "pageid": 500 + i, "title": f"File:{title}.jpg",
                "imageinfo": [{
                    "mime": "image/png", "width": w, "height": h, "thumburl": f"{base}/img/{pid}.png",
                    "thumbwidth": w, "thumbheight": h, "descriptionurl": f"https://commons.example/{pid}",
                    "extmetadata": {"Artist": {"value": '<a href="//x">Luca &amp; Co</a>'},
                                    "LicenseShortName": {"value": "CC BY-SA 4.0"}},
                }],
            }
            for i, (pid, title, w, h) in enumerate(chunk, start=offset)
        }
        out: dict = {"query": {"pages": pages}} if pages else {}
        if offset + SERVER_PAGE < len(hits):
            out["continue"] = {"gsroffset": offset + SERVER_PAGE, "continue": "gsroffset||"}
        return jsonify(out)

    # --- finta API Openverse (nessuna chiave) ---------------------------------
    @app.get("/v1/images/")
    def openverse_images():
        query = request.args.get("q", "").lower()
        wanted = request.args.get("aspect_ratio")
        page = request.args.get("page", 1, type=int)
        base = request.host_url.rstrip("/")
        kind = lambda w, h: "square" if w == h else "tall" if h > w else "wide"  # noqa: E731
        hits = [
            {"id": f"uuid-{pid}", "title": title, "url": f"{base}/img/{pid}.png", "creator": "Anna Verdi",
             "license": "by", "license_version": "4.0", "source": "flickr",
             "foreign_landing_url": f"https://example.org/{pid}", "width": None, "height": None}
            for pid, title, desc, w, h, _b in PINS
            if query in f"{title} {desc}".lower() and (not wanted or wanted == kind(w, h))
        ]
        chunk = hits[(page - 1) * SERVER_PAGE : page * SERVER_PAGE]
        return jsonify(results=chunk, page_count=max(1, -(-len(hits) // SERVER_PAGE)))

    return app
