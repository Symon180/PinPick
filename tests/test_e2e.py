"""Test end-to-end: browser reale contro il portale demo locale."""
import pytest

from portalfetch.config import Config
from portalfetch.engine import exit_code, run

SEL = {"user": "#user", "password": "#password", "submit": "#submit",
       "logged_in": "#area", "error": ".error", "links": "a.inv", "next": "#next"}


def make_config(tmp_path, url, kind="generic"):
    return Config(
        download_dir=tmp_path / "dl",
        tracking_file=tmp_path / "tracking.json",
        sites={"demo": {"type": kind, "url": f"{url}/login", "selectors": SEL}},
    )


@pytest.fixture(autouse=True)
def creds(monkeypatch):
    monkeypatch.setenv("PORTALFETCH_DEMO_USER", "demo")
    monkeypatch.setenv("PORTALFETCH_DEMO_PASSWORD", "demo123")


async def test_scarica_tutto_con_paginazione_e_poi_salta_i_gia_scaricati(tmp_path, demo_url):
    cfg = make_config(tmp_path, demo_url)
    [r1] = await run(cfg)
    assert r1.error is None and len(r1.downloaded) == 12  # 3 pagine da 5/5/2
    files = sorted((tmp_path / "dl" / "demo").glob("*.pdf"))
    assert len(files) == 12 and files[0].read_bytes().startswith(b"%PDF")

    [r2] = await run(cfg)  # secondo giro: niente da fare
    assert r2.downloaded == [] and r2.skipped == 12
    assert exit_code([r1, r2]) == 0


async def test_plugin_in_codice_con_api_json(tmp_path, demo_url):
    [r] = await run(make_config(tmp_path, demo_url, kind="demo_api"))
    assert r.error is None and len(r.downloaded) == 12


async def test_password_errata_non_scarica_nulla(tmp_path, demo_url, monkeypatch):
    monkeypatch.setenv("PORTALFETCH_DEMO_PASSWORD", "sbagliata")
    [r] = await run(make_config(tmp_path, demo_url))
    assert r.error and "accesso rifiutato" in r.error and r.downloaded == []
    assert exit_code([r]) == 1


async def test_scan_only_non_scrive_file(tmp_path, demo_url):
    [r] = await run(make_config(tmp_path, demo_url), scan_only=True)
    assert len(r.downloaded) == 12 and not (tmp_path / "dl").exists()
