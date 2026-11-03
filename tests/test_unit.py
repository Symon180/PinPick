import json
import random

import pytest

from pinpick.downloader import History, safe_filename
from pinpick.errors import ConfigError
from pinpick.models import Photo
from pinpick.picker import select
from pinpick.sources.pinterest import parse_pin


def photo(i, w, h, title="", desc="", board=""):
    return Photo(str(i), title, desc, f"http://x/{i}.png", w, h, board)


PHOTOS = [
    photo(1, 300, 200, "Mare", "Sardegna", "Viaggi"),
    photo(2, 200, 300, "Monti", "Dolomiti", "Viaggi"),
    photo(3, 100, 100, "Pizza", "", "Cucina"),
]


def test_orientamento():
    assert [p.orientation for p in PHOTOS] == ["landscape", "portrait", "square"]


def test_parola_chiave_senza_maiuscole_e_su_bacheca():
    assert [p.id for p in select(PHOTOS, "MARE", count=9)] == ["1"]
    assert {p.id for p in select(PHOTOS, "cucina", count=9)} == {"3"}
    assert len(select(PHOTOS, "", count=9)) == 3


def test_filtro_orientamento_e_conteggio_massimo():
    assert [p.id for p in select(PHOTOS, orientation="portrait", count=5)] == ["2"]
    assert len(select(PHOTOS, count=99)) == 3  # non ne inventa


def test_esclude_gia_scaricate_e_scelta_riproducibile():
    assert {p.id for p in select(PHOTOS, count=9, exclude_ids={"1", "2"})} == {"3"}
    a = select(PHOTOS, count=2, rng=random.Random(7))
    b = select(PHOTOS, count=2, rng=random.Random(7))
    assert a == b


def test_parametri_non_validi():
    with pytest.raises(ConfigError):
        select(PHOTOS, orientation="diagonale")
    with pytest.raises(ConfigError):
        select(PHOTOS, count=0)


def test_parse_pin_scarta_video_e_usa_originale():
    assert parse_pin({"id": "v", "media": {"media_type": "video"}}) is None
    assert parse_pin({"id": "x", "media": {"media_type": "image", "images": {}}}) is None
    p = parse_pin({"id": "9", "title": None, "media": {"images": {
        "150x150": {"url": "s", "width": 150, "height": 150},
        "originals": {"url": "big", "width": 800, "height": 600}}}}, "Bacheca")
    assert (p.url, p.title, p.board) == ("big", "", "Bacheca")


def test_safe_filename_blocca_path_traversal():
    assert "/" not in safe_filename("../../etc/passwd") and "\\" not in safe_filename("..\\x")
    assert safe_filename("a:b*c?") == "a_b_c_"
    assert safe_filename("...") == "foto"


def test_history_persistente_e_file_corrotto(tmp_path):
    f = tmp_path / "h.json"
    History(f).add("a")
    assert History(f).ids == {"a"}
    f.write_text("{rotto", encoding="utf-8")
    assert History(f).ids == set()
    assert f.with_suffix(".corrotto").exists()
    assert History(tmp_path / "nuovo.json").ids == set()
