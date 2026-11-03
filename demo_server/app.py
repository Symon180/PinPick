"""Portale fittizio con login e fatture PDF finte, per provare PortalFetch senza siti reali.

Avvio:  python -m demo_server           (http://127.0.0.1:8765, utente demo / password demo123)
"""
from __future__ import annotations

from flask import Flask, Response, jsonify, redirect, render_template_string, request, session, url_for

USER, PASSWORD = "demo", "demo123"
PAGE_SIZE = 5
INVOICES = [{"id": i, "number": f"FAT-2026-{i:03d}", "pdf": f"/download/{i}.pdf"} for i in range(1, 13)]

LOGIN = """<!doctype html><title>Demo Portal</title><h1>Accesso</h1>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post"><input id="user" name="user"><input id="password" name="password" type="password">
<button id="submit" type="submit">Entra</button></form>"""

LIST = """<!doctype html><title>Fatture</title><h1 id="area">Area riservata</h1>
<table>{% for inv in invoices %}<tr><td><a class="inv" href="{{ inv.pdf }}">{{ inv.number }}</a></td></tr>{% endfor %}</table>
{% if next_page %}<a id="next" href="{{ url_for('invoices', page=next_page) }}">Avanti</a>{% endif %}
<a id="logout" href="{{ url_for('logout') }}">Esci</a>"""


def fake_pdf(number: str) -> bytes:
    return (f"%PDF-1.4\n% fattura fittizia {number}\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n").encode()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "solo-per-la-demo"

    def logged() -> bool:
        return session.get("ok") is True

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if request.form.get("user") == USER and request.form.get("password") == PASSWORD:
                session["ok"] = True
                return redirect(url_for("invoices"))
            return render_template_string(LOGIN, error="Credenziali non valide"), 401
        return render_template_string(LOGIN, error=None)

    @app.route("/invoices")
    def invoices():
        if not logged():
            return redirect(url_for("login"))
        page = max(1, request.args.get("page", 1, type=int))
        chunk = INVOICES[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        has_next = page * PAGE_SIZE < len(INVOICES)
        return render_template_string(LIST, invoices=chunk, next_page=page + 1 if has_next else None)

    @app.route("/api/invoices")
    def api_invoices():
        if not logged():
            return jsonify(error="non autenticato"), 401
        return jsonify(INVOICES)

    @app.route("/download/<int:inv_id>.pdf")
    def download(inv_id: int):
        if not logged():
            return Response("non autenticato", 401)
        number = f"FAT-2026-{inv_id:03d}"
        return Response(fake_pdf(number), mimetype="application/pdf")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    return app
