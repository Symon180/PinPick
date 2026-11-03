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
