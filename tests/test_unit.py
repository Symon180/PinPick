import json

import pytest

from portalfetch.config import credentials_for, load_config
from portalfetch.engine import safe_filename
from portalfetch.errors import ConfigError
from portalfetch.registry import get_portal_class
from portalfetch.tracking import Tracking


def test_safe_filename_blocca_path_traversal():
    assert "/" not in safe_filename("../../etc/passwd")
    assert "\\" not in safe_filename("..\\..\\win.ini")
    assert safe_filename("a:b*c?.pdf") == "a_b_c_.pdf"
    assert safe_filename("...") == "documento"


def test_tracking_persiste_e_gestisce_file_corrotto(tmp_path):
    f = tmp_path / "t.json"
    t = Tracking(f)
    t.mark_done("s", "1")
    assert Tracking(f).is_done("s", "1")
    assert not Tracking(f).is_done("s", "2")
    f.write_text("{non json", encoding="utf-8")
    assert not Tracking(f).is_done("s", "1")
    assert f.with_suffix(".corrotto").exists()  # il file danneggiato non viene perso


def test_registry_tipo_sconosciuto():
    with pytest.raises(ConfigError):
        get_portal_class("non_esiste")
    assert get_portal_class("generic") and get_portal_class("demo_api")


def test_config_valida_e_percorsi_relativi(tmp_path):
    (tmp_path / "s.yaml").write_text("sites:\n  a: {type: generic}\n", encoding="utf-8")
    cfg = load_config(tmp_path / "s.yaml")
    assert cfg.download_dir == (tmp_path / "downloads").resolve()


@pytest.mark.parametrize("body", ["", "sites: {}", "sites:\n  a: {url: x}\n"])
def test_config_non_valida(tmp_path, body):
    (tmp_path / "s.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "s.yaml")


def test_credenziali_da_ambiente(monkeypatch):
    monkeypatch.delenv("PORTALFETCH_X_Y_USER", raising=False)
    with pytest.raises(ConfigError):
        credentials_for("x-y")
    monkeypatch.setenv("PORTALFETCH_X_Y_USER", "u")
    monkeypatch.setenv("PORTALFETCH_X_Y_PASSWORD", "p")
    assert credentials_for("x-y") == ("u", "p")
