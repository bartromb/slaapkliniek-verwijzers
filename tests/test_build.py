"""tests/test_build.py — de harde randvoorwaarden uit CLAUDE.md §3, afgedwongen op dist/.

Draait build.py eerst (in een tijdelijke kopie zodat een lokale dist/ niet meetelt), en toetst:
i18n-pariteit, geen inline <script>/<style>/on*=-attributen, geen externe URL's buiten de
toegestane hosts, geen fetch/XHR/opslag in de JS, geen form action, PDF-bestandsnaam zonder
patiëntnaam, CSP-headers in de nginx-config, placeholders verborgen, en de scores.js-tests in V8.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LANGS = ["nl", "fr", "en", "de"]


@pytest.fixture(scope="session")
def dist(tmp_path_factory) -> Path:
    werk = tmp_path_factory.mktemp("bouw")
    for naam in ("build.py", "CHANGELOG.md", "config", "i18n", "templates", "static", "vendor"):
        bron = ROOT / naam
        if bron.is_dir():
            shutil.copytree(bron, werk / naam)
        else:
            shutil.copy(bron, werk / naam)
    r = subprocess.run([sys.executable, "build.py"], cwd=werk, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return werk / "dist"


def _paginas(dist: Path) -> list[Path]:
    return sorted(dist.rglob("*.html"))


def _site() -> dict:
    return json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))


# ── i18n ────────────────────────────────────────────────────────────────────────
def test_i18n_alle_talen_dezelfde_sleutels():
    nl = json.loads((ROOT / "i18n" / "nl.json").read_text(encoding="utf-8"))
    for lang in LANGS[1:]:
        d = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        assert set(d) == set(nl), f"{lang}: ontbreekt {sorted(set(nl) - set(d))}, extra {sorted(set(d) - set(nl))}"
        assert all(isinstance(v, str) and v.strip() for v in d.values()), f"{lang}: lege waarde"


def test_i18n_vertalingen_zijn_geen_kopieen():
    nl = json.loads((ROOT / "i18n" / "nl.json").read_text(encoding="utf-8"))
    for lang in ("fr", "en", "de"):
        d = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        gelijk = [k for k in nl if d[k] == nl[k] and len(nl[k]) > 12]
        assert len(gelijk) < 8, f"{lang}: {len(gelijk)} lange strings identiek aan nl: {gelijk[:5]}"


# ── dist ────────────────────────────────────────────────────────────────────────
def test_dist_bevat_alle_paginas(dist):
    for lang in LANGS:
        for pad in ("", "aanvraag/", "consult/"):
            assert (dist / lang / pad / "index.html").exists(), f"{lang}/{pad}"
    assert (dist / "index.html").exists()
    assert (dist / "vendor" / "jspdf.umd.min.js").exists() and (dist / "vendor" / "jspdf.LICENSE").exists()


def test_geen_inline_scripts_of_styles(dist):
    for p in _paginas(dist):
        html = p.read_text(encoding="utf-8")
        for m in re.finditer(r"<script\b([^>]*)>", html, re.I):
            attrs = m.group(1)
            assert re.search(r'\bsrc=', attrs) or 'type="application/json"' in attrs, f"{p}: inline script {attrs!r}"
        assert "<style" not in html.lower(), f"{p}: inline <style>"
        assert not re.search(r'\sstyle="', html, re.I), f"{p}: style-attribuut"
        assert not re.search(r'\son[a-z]+="', html, re.I), f"{p}: on*-attribuut"
        assert "javascript:" not in html.lower(), f"{p}: javascript:-URL"


def test_geen_externe_urls_buiten_toegestane_hosts(dist):
    toegestaan = set(_site().get("toegestane_externe_hosts", []))
    site_url = _site().get("site_url", "")
    if site_url:
        toegestaan.add(re.sub(r"^https?://", "", site_url).split("/")[0])
    for p in list(_paginas(dist)) + [dist / "static" / "css" / "verwijzers.css"]:
        for host in re.findall(r"https?://([A-Za-z0-9.\-]+)", p.read_text(encoding="utf-8")):
            assert host in toegestaan, f"{p}: externe host {host}"


def test_js_verlaat_de_browser_niet():
    verboden = ["fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "localStorage", "sessionStorage",
                "indexedDB", "document.cookie", "EventSource", "importScripts"]
    for p in (ROOT / "static" / "js").glob("*.js"):
        code = p.read_text(encoding="utf-8")
        for v in verboden:
            assert v not in code, f"{p.name} gebruikt {v}"


def test_formulier_heeft_geen_action_en_knoppen_zijn_geen_submit(dist):
    html = (dist / "nl" / "aanvraag" / "index.html").read_text(encoding="utf-8")
    for m in re.finditer(r"<form\b([^>]*)>", html, re.I):
        assert "action=" not in m.group(1), "form met action"
        assert "method=" not in m.group(1), "form met method"
    assert 'type="submit"' not in html


def test_pdf_bestandsnaam_zonder_patientnaam():
    code = (ROOT / "static" / "js" / "pdf.js").read_text(encoding="utf-8")
    assert "bestandsnaam(t('js.pdf_bestandsnaam')" in code
    assert "patient.naam" not in code.split("function bestandsnaam")[1].split("function maak")[0]


def test_placeholders_zijn_verborgen(dist):
    for p in _paginas(dist):
        html = p.read_text(encoding="utf-8")
        assert "&lt;...&gt;" not in html and "<...>" not in html, f"{p}: placeholder zichtbaar"
        assert "exacte dienstnaam" not in html, f"{p}: placeholder dienstnaam zichtbaar"


def test_nginx_csp_en_no_store():
    conf = (ROOT / "nginx" / "default.conf").read_text(encoding="utf-8") + \
           (ROOT / "nginx" / "security-headers.conf").read_text(encoding="utf-8")
    for eis in ("connect-src 'none'", "form-action 'none'", "frame-ancestors 'none'", "base-uri 'none'",
                "script-src 'self'", "Referrer-Policy \"no-referrer\"", "no-store"):
        assert eis in conf, eis
    assert "'unsafe-inline'" not in conf and "'unsafe-eval'" not in conf


def test_privacyvoetnoot_op_elke_pagina(dist):
    for lang in LANGS:
        s = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        for pad in ("", "aanvraag/", "consult/"):
            html = (dist / lang / pad / "index.html").read_text(encoding="utf-8")
            assert s["footer.privacy"] in html, f"{lang}/{pad}"


def test_scores_js_in_v8():
    racer = pytest.importorskip("py_mini_racer")
    ctx = racer.MiniRacer()
    ctx.eval((ROOT / "static" / "js" / "scores.js").read_text(encoding="utf-8"))
    ctx.eval((ROOT / "tests" / "test_scores.js").read_text(encoding="utf-8"))
    assert str(ctx.eval("globalThis.__RESULT")).startswith("OK"), ctx.eval("globalThis.__RESULT")


def test_pdf_bestandsnaam_en_ascii_in_v8():
    racer = pytest.importorskip("py_mini_racer")
    ctx = racer.MiniRacer()
    ctx.eval((ROOT / "static" / "js" / "pdf.js").read_text(encoding="utf-8"))
    assert ctx.eval("globalThis.Pdf.bestandsnaam('verwijsbrief_slaapkliniek', '2026-09-30T12:00:00')") == "verwijsbrief_slaapkliniek_20260930.pdf"
    assert ctx.eval("globalThis.Pdf.bestandsnaam('Jan Janssen/../x', '2026-09-30T12:00:00')") == "Jan_Janssen____x_20260930.pdf"
    assert ctx.eval("globalThis.Pdf.ascii('STOP-BANG 5 \\u2265 5 \\u2192 PG \\u00b7 ok')") == "STOP-BANG 5 >= 5 -> PG - ok"


def test_pdf_maak_met_jspdf_in_v8():
    """De hele verwijsbrief-PDF, met de vendored jsPDF, zonder browser: minimale stubs voor de
    globals die jsPDF bij het laden aanraakt. Bewijst dat pdf.js en jsPDF 2.5.2 bij elkaar passen."""
    racer = pytest.importorskip("py_mini_racer")
    ctx = racer.MiniRacer()
    ctx.eval("var window = globalThis; var self = globalThis; var navigator = {userAgent: 'v8'};"
             "var document = {createElement: function(){return {getContext: function(){return null}, style: {}}},"
             " createElementNS: function(){return {}}}; var atob = function(s){return s}; var btoa = function(s){return s};")
    ctx.eval((ROOT / "vendor" / "jspdf.umd.min.js").read_text(encoding="utf-8"))
    ctx.eval((ROOT / "static" / "js" / "pdf.js").read_text(encoding="utf-8"))
    nl = json.loads((ROOT / "i18n" / "nl.json").read_text(encoding="utf-8"))
    ctx.eval("var I18N = " + json.dumps(nl) + "; var t = function(k){ return I18N[k] || k; };")
    data = {
        "verwijzer": {"naam": "Dr. Test", "riziv": "1-23456-78-901", "adres": "Straat 1", "tel": "09 000 00 00"},
        "patient": {"naam": "Voorbeeld Patiënt", "geboortedatum": "1970-06-15", "geslacht": "m", "geslachtLabel": "Man", "rrn": ""},
        "onderzoek": {"code": "pg", "label": "Polygrafie", "campus": "", "campusLabel": "Geen voorkeur"},
        "urgentie": {"code": "normaal", "label": "Normaal", "toelichting": ""},
        "klachten": ["Snurken"], "lengte": "180", "gewicht": "95", "bmi": 29.3, "hals": "42",
        "ess": {"totaal": 12, "items": [1, 2, 1, 2, 1, 2, 1, 2], "interpretatie": "verhoogde slaperigheid (11–24)"},
        "stopbang": {"totaal": 6, "items": {}, "itemsTekst": "S+ T+ O+ P- B- A+ N+ G+"},
        "comorbiditeit": [], "medicatie": "", "eerder": {"ja": False, "toelichting": ""},
        "vraagstelling": "Vermoeden OSAS — graag polygrafie. " * 12,
        "keuzehulpTekst": "Suggestie: polygrafie — hoge voorafkans (STOP-BANG 6 ≥ 5).",
    }
    ctx.eval("var DATA = " + json.dumps(data) + ";")
    naam = ctx.eval("globalThis.Pdf.maak(DATA, t, {jsPDF: window.jspdf.jsPDF, nietOpslaan: true, vandaag: '2026-09-30T10:00:00'})")
    assert naam == "verwijsbrief_slaapkliniek_20260930.pdf"
    assert "Voorbeeld" not in naam
    kop = ctx.eval("(function(){ var d = new window.jspdf.jsPDF({unit:'mm', format:'a4'}); d.text('x', 10, 10); return d.output().slice(0, 5); })()")
    assert kop == "%PDF-"


def test_consult_login_gaat_rechtstreeks_naar_het_portaal_per_taal(dist):
    """Geen tussenstap via de nexuzhealth-marketingpagina: de knop gaat naar het pro-portaal,
    dat meteen de login start, met de taal van de pagina."""
    for lang in LANGS:
        html = (dist / lang / "consult" / "index.html").read_text(encoding="utf-8")
        assert f'href="https://mynexuzpro.nexuzhealth.be/?language={lang}"' in html, lang
        assert f"lang={lang}&amp;target=clinicus" in html, lang
        assert "{lang}" not in html


def test_aliasdomeinen_verwijzen_naar_het_canonieke_portaal_per_taal():
    conf = (ROOT / "nginx" / "default.conf").read_text(encoding="utf-8")
    for d in ("slaapstudie.be", "slaapstudie.eu", "slaapstudie.com", "etudedusommeil.be", "etudedusommeil.eu", "etudedusommeil.com"):
        assert f" {d} " in conf.replace("\n", " ") and f"www.{d}" in conf, d
    assert "return 301 https://verwijzers.slaapkliniek.be/$alias_lang$request_uri" in conf
    assert "~*etudedusommeil\\." in conf and "default                 nl" in conf
    assert "listen 80 default_server" in conf, "het portaal zelf moet de default server blijven"
