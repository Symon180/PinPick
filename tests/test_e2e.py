"""End-to-end: client reale contro la finta API Pinterest (nessuna rete, nessun token vero)."""
import pytest

from pinpick.cli import main
from pinpick.errors import ApiError, AuthError
from pinpick.sources.pinterest import PinterestSource


@pytest.fixture(autouse=True)
def env(monkeypatch, api_url):
    monkeypatch.setenv("PINPICK_API_BASE", api_url)
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "demo-token")


def test_legge_tutte_le_pagine_e_salta_i_video(api_url):
    photos = list(PinterestSource("demo-token", api_url).photos())
    assert sorted(p.id for p in photos) == [f"p{i}" for i in range(1, 9)]  # 8 foto, paginate da 4


def test_token_sbagliato(api_url):
    with pytest.raises(AuthError):
        list(PinterestSource("sbagliato", api_url).photos())


def test_server_non_raggiungibile():
    with pytest.raises(ApiError):
        list(PinterestSource("t", "http://127.0.0.1:1").photos())


def test_cli_scarica_foto_filtrate(tmp_path, capsys):
    code = main(["-k", "mare", "-o", "landscape", "-n", "1", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0 and "Scaricata" in out
    [img] = [p for p in tmp_path.iterdir() if p.suffix == ".png"]
    assert img.read_bytes().startswith(b"\x89PNG") and img.stat().st_size > 100


def test_cli_non_riscarica_le_stesse(tmp_path):
    args = ["-k", "pizza", "--out", str(tmp_path)]
    assert main(args) == 0
    assert main(args) == 1  # l'unica "pizza" e gia stata scaricata
    assert main(args + ["--allow-repeats"]) == 0


def test_cli_nessun_risultato(tmp_path, capsys):
    assert main(["-k", "inesistente", "--out", str(tmp_path)]) == 1


def test_cli_senza_token(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PINTEREST_ACCESS_TOKEN")
    assert main(["--out", str(tmp_path)]) == 2
    assert "PINTEREST_ACCESS_TOKEN" in capsys.readouterr().err


def test_cli_token_rifiutato(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "scaduto")
    assert main(["--out", str(tmp_path)]) == 2
    assert "token" in capsys.readouterr().err


# --- Pexels (stessa finta API, chiave demo-key) --------------------------------
from pinpick.sources.pexels import PexelsSource, parse_photo  # noqa: E402


def test_pexels_ricerca_per_parola_chiave_con_paginazione(api_url):
    ids = {p.id for p in PexelsSource("demo-key", api_url).photos("a")}  # "a" compare in quasi tutti i testi
    assert len(ids) >= 5  # piu di una pagina da 4
    assert all(i.startswith("pexels-") for i in ids)


def test_pexels_filtra_orientamento_sul_server(api_url):
    photos = list(PexelsSource("demo-key", api_url).photos("", "portrait"))
    assert photos and all(p.orientation == "portrait" for p in photos)


def test_pexels_chiave_sbagliata(api_url):
    with pytest.raises(AuthError):
        list(PexelsSource("no", api_url).photos("mare"))


def test_pexels_parse_scarta_voci_senza_immagine():
    assert parse_photo({"id": 1, "src": {}}) is None
    p = parse_photo({"id": 5, "alt": "x", "width": 10, "height": 20, "photographer": "Anna",
                     "url": "u", "src": {"large": "L"}})
    assert p.id == "pexels-5" and "Anna" in p.credit and p.orientation == "portrait"


def test_cli_pexels_scarica_e_mostra_il_credito(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PEXELS_API_KEY", "demo-key")
    assert main(["-s", "pexels", "-k", "pizza", "-n", "1", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Credito: Mario Rossi (Pexels)" in out
    assert any(p.suffix == ".png" for p in tmp_path.iterdir())


def test_cli_pexels_senza_chiave(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    assert main(["-s", "pexels", "--out", str(tmp_path)]) == 2
    assert "PEXELS_API_KEY" in capsys.readouterr().err


# --- Openverse (nessuna chiave) -------------------------------------------------
from pinpick.sources.openverse import OpenverseSource, parse_image  # noqa: E402


def test_openverse_ricerca_con_paginazione_e_credito(api_url):
    photos = list(OpenverseSource(api_url).photos("a"))  # "a" compare in quasi tutti i testi
    assert len(photos) >= 5 and all(p.id.startswith("openverse-") for p in photos)
    assert "Anna Verdi" in photos[0].credit and "CC BY 4.0" in photos[0].credit


def test_openverse_senza_parola_chiave(api_url):
    with pytest.raises(ApiError):
        list(OpenverseSource(api_url).photos(""))


def test_openverse_parse_scarta_voci_incomplete():
    assert parse_image({"id": "x"}) is None and parse_image({"url": "u"}) is None


def test_cli_openverse_con_orientamento_senza_dimensioni(tmp_path, capsys):
    # le dimensioni possono mancare: il filtro orientamento lo fa il server
    assert main(["-s", "openverse", "-k", "pizza", "-o", "landscape", "--out", str(tmp_path)]) == 0
    assert "Credito: Anna Verdi" in capsys.readouterr().out


def test_cli_openverse_nessun_risultato(tmp_path):
    assert main(["-s", "openverse", "-k", "zzzz", "--out", str(tmp_path)]) == 1


# --- Wikimedia Commons (nessuna chiave) ------------------------------------------
from pinpick.sources.wikimedia import WikimediaSource, parse_page  # noqa: E402


def test_wikimedia_ricerca_paginata_e_filtro_orientamento(api_url):
    tutte = list(WikimediaSource(api_url).photos("a"))
    assert len(tutte) >= 5 and all(p.id.startswith("commons-") for p in tutte)
    verticali = list(WikimediaSource(api_url).photos("a", "portrait"))
    assert verticali and all(p.orientation == "portrait" for p in verticali)


def test_wikimedia_credito_ripulito_dall_html(api_url):
    [p, *_] = list(WikimediaSource(api_url).photos("pizza"))
    assert "Luca & Co" in p.credit and "<a" not in p.credit and "CC BY-SA 4.0" in p.credit


def test_wikimedia_senza_parola_chiave(api_url):
    with pytest.raises(ApiError):
        list(WikimediaSource(api_url).photos(""))


def test_wikimedia_parse_scarta_formati_non_immagine():
    assert parse_page({"pageid": 1, "title": "File:x.ogg", "imageinfo": [{"mime": "audio/ogg", "url": "u"}]}) is None
    assert parse_page({"pageid": 2, "title": "File:x.jpg"}) is None


def test_cli_wikimedia_scarica_con_credito(tmp_path, capsys):
    assert main(["-s", "wikimedia", "-k", "pizza", "--out", str(tmp_path)]) == 0
    assert "Credito: Luca & Co" in capsys.readouterr().out
