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


BRONNEN = ("build.py", "CHANGELOG.md", "config", "i18n", "templates", "static", "vendor")


def bouw_kopie(werk: Path, wijzig=None) -> Path:
    """Kopieert de bronnen naar `werk`, past `wijzig(werk)` toe en draait build.py. Geeft dist/."""
    werk.mkdir(parents=True, exist_ok=True)
    for naam in BRONNEN:
        bron = ROOT / naam
        if bron.is_dir():
            shutil.copytree(bron, werk / naam)
        else:
            shutil.copy(bron, werk / naam)
    if wijzig:
        wijzig(werk)
    r = subprocess.run([sys.executable, "build.py"], cwd=werk, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return werk / "dist"


@pytest.fixture(scope="session")
def dist(tmp_path_factory) -> Path:
    return bouw_kopie(tmp_path_factory.mktemp("bouw"))


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


def test_consult_login_gaat_rechtstreeks_naar_het_portaal_per_taal(dist):
    """Geen tussenstap via de nexuzhealth-marketingpagina: de knop gaat naar het pro-portaal,
    dat meteen de login start, met de taal van de pagina."""
    for lang in LANGS:
        html = (dist / lang / "consult" / "index.html").read_text(encoding="utf-8")
        assert f'href="https://mynexuzpro.nexuzhealth.be/?language={lang}"' in html, lang
        assert f"lang={lang}&amp;target=clinicus" in html, lang
        assert "{lang}" not in html


def test_campussen_op_infopagina_en_in_dropdown(dist):
    site = _site()
    namen = [c["naam"] for c in site["campussen"]]
    assert namen == ["Campus Aalst — Moorselbaan", "Campus Aalst — Merestraat", "Campus Asse", "Campus Wetteren", "Campus Geraardsbergen"]
    for lang in LANGS:
        info = (dist / lang / "index.html").read_text(encoding="utf-8")
        form = (dist / lang / "aanvraag" / "index.html").read_text(encoding="utf-8")
        for naam in namen:
            assert naam in info and naam in form, (lang, naam)
        assert 'value="aalst-moorselbaan"' in form


def test_elke_taal_heeft_haar_eigen_video(dist):
    for lang in LANGS:
        html = (dist / lang / "index.html").read_text(encoding="utf-8")
        assert f"static/video/verwijzers_demo_{lang}.mp4" in html and f"verwijzers_demo_{lang}.jpg" in html, lang
        assert (ROOT / "static" / "video" / f"verwijzers_demo_{lang}.mp4").stat().st_size > 1_000_000, lang


# ── v0.2.0: velden.json, kopieertekst, conventie, eHealthBox, domeinen ─────────────────────
def _velden() -> dict:
    return json.loads((ROOT / "config" / "velden.json").read_text(encoding="utf-8"))


def _v8():
    racer = pytest.importorskip("py_mini_racer")
    return racer.MiniRacer()


def test_velden_json_is_geldig_en_draagt_een_versie():
    v = _velden()
    assert re.fullmatch(r"\d{4}-\d{2}-[a-z]", v["versie"])
    ids = [x["id"] for x in v["velden"]]
    assert len(ids) == len(set(ids))
    assert sum(1 for x in v["velden"] if x["conventie"]) >= 10
    # patiëntnaam en rijksregisternummer horen nooit in de kopieertekst
    per = {x["id"]: x for x in v["velden"]}
    assert per["patient_naam"]["kopie_label"] is None and per["patient_rrn"]["kopie_label"] is None
    # prioriteit 1 voor wat nooit mag wegvallen
    for vid in ("onderzoek", "stopbang_totaal", "ess_totaal", "bmi", "vraagstelling", "verwijzer_naam", "verwijzer_riziv"):
        assert per[vid]["kopie_prioriteit"] == 1, vid


def test_een_fout_in_velden_json_breekt_de_build(tmp_path):
    for naam in BRONNEN:
        bron = ROOT / naam
        shutil.copytree(bron, tmp_path / naam) if bron.is_dir() else shutil.copy(bron, tmp_path / naam)
    f = tmp_path / "config" / "velden.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["velden"][0]["label_key"] = "bestaat.niet"
    d["velden"][1]["type"] = "onzin"
    f.write_text(json.dumps(d), encoding="utf-8")
    r = subprocess.run([sys.executable, "build.py", "--check"], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode != 0 and "bestaat.niet" in (r.stdout + r.stderr) and "onzin" in (r.stdout + r.stderr)


def test_formulier_komt_volledig_uit_velden_json(tmp_path):
    """Een veld toevoegen vraagt geen template- of JS-wijziging: alleen velden.json (+ een label)."""
    def wijzig(werk):
        f = werk / "config" / "velden.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["velden"].append({"id": "nieuw_testveld", "type": "tekst", "label_key": "aanvraag.medicatie", "verplicht": False,
                            "conventie": True, "kopie_label": None, "kopie_prioriteit": None, "kopie_regel": None, "sectie": "leefstijl"})
        f.write_text(json.dumps(d), encoding="utf-8")
    d2 = bouw_kopie(tmp_path, wijzig)
    for lang in LANGS:
        html = (d2 / lang / "aanvraag" / "index.html").read_text(encoding="utf-8")
        assert 'id="nieuw_testveld"' in html and 'data-veld="nieuw_testveld"' in html, lang
        assert '"nieuw_testveld"' in html.split('id="velden">')[1], "de definitie gaat ook mee naar de JS"


def test_elk_veld_uit_velden_json_staat_in_het_formulier(dist):
    html = (dist / "nl" / "aanvraag" / "index.html").read_text(encoding="utf-8")
    for v in _velden()["velden"]:
        assert f'data-veld="{v["id"]}"' in html, v["id"]
    assert 'id="knop_kopieer"' in html and 'id="kopie_voorbeeld"' in html and "readonly" in html
    assert 'id="kopie_melding" aria-live="polite"' in html
    assert 'id="conventie_teller"' in html


def test_conventielabel_zegt_vermoedelijk(dist):
    for lang, woord in (("nl", "Vermoedelijk"), ("fr", "Probablement"), ("en", "Probably"), ("de", "Voraussichtlich")):
        html = (dist / lang / "aanvraag" / "index.html").read_text(encoding="utf-8")
        assert woord in html, lang
    for lang in LANGS:
        s_ = (ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8").lower()
        assert "verplicht voor de conventie" not in s_ and "obligatoire pour la convention" not in s_


def test_kopieer_js_in_v8():
    ctx = _v8()
    ctx.eval((ROOT / "static" / "js" / "kopieer.js").read_text(encoding="utf-8"))
    ctx.eval((ROOT / "tests" / "test_kopieer.js").read_text(encoding="utf-8"))
    assert str(ctx.eval("globalThis.__RESULT_KOPIEER")).startswith("OK"), ctx.eval("globalThis.__RESULT_KOPIEER")


VOORBEELD = {
    "verwijzer_naam": "dr. An Voorbeeld", "verwijzer_riziv": "1-23456-78-901", "verwijzer_adres": "Dorpsstraat 1", "verwijzer_tel": "",
    "patient_naam": "ZEERUNIEKENAAM Jan", "patient_geboortedatum": "1968-03-12", "patient_geslacht": "m", "patient_rrn": "68031212345",
    "onderzoek": "psg", "campus": "wetteren", "urgentie": "verhoogd", "urgentie_toelichting": "beroepschauffeur", "beroepschauffeur": "ja",
    "klachten": ["snurken", "apneus", "nycturie"], "slaperig_stuur": "ja", "lengte": "178", "gewicht": "105", "bmi": 33.1, "hals": "43",
    "ess_totaal": 14, "sb_s": "ja", "sb_t": "ja", "sb_o": "ja", "sb_p": "ja", "sb_b": "nee", "sb_a": "ja", "sb_n": "ja", "sb_g": "ja", "stopbang_totaal": 7,
    "cv": ["hypertensie_resistent", "vkf"], "dm2": "ja", "andere_comorbiditeit": [], "eerder_onderzoek": "ja", "eerder_type": "pg", "eerder_datum": "2021",
    "eerder_ahi": "22", "cpap_mra": "nee", "cpap_toelichting": "", "roken": "gestopt", "alcohol": "matig", "medicatie": "bisoprolol, apixaban, metformine",
    "vraagstelling": "OSA? Graag beoordeling, rijgeschiktheid.",
}


def _kopie(lang: str, data: dict, max_tekens: int = 1000) -> dict:
    ctx = _v8()
    ctx.eval((ROOT / "static" / "js" / "kopieer.js").read_text(encoding="utf-8"))
    velden = _velden()
    site = _site()
    for v in velden["velden"]:
        if v.get("opties_bron") == "campussen":
            v["opties"] = [{"waarde": c["id"], "label": c["naam"]} for c in site["campussen"]]
    i18n = json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
    for i in range(1, 9):
        data.setdefault(f"ess_{i}", "2")
    ctx.eval("var DEF = " + json.dumps(velden) + "; var I = " + json.dumps(i18n) + "; var D = " + json.dumps(data) + ";")
    uit = ctx.eval("JSON.stringify(Kopieer.genereerTekst(D, DEF, '%s', {t: function(k){ if (I[k] === undefined) throw new Error('sleutel ' + k); return I[k]; },"
                   " max: %d, maxVrij: 160, kliniek: 'Slaapkliniek AZORG'}))" % (lang, max_tekens))
    return json.loads(uit)


def test_kopieertekst_met_de_echte_velden_nl():
    r = _kopie("nl", dict(VOORBEELD))
    regels = r["tekst"].split("\n")
    assert regels[0] == "AANVRAAG SLAAPONDERZOEK – Slaapkliniek AZORG [form %s]" % _velden()["versie"]
    assert "Gevraagd: PSG | Voorkeur: Campus Wetteren | Urgentie: verhoogd (beroepschauffeur) | beroepschauffeur/veiligheidsfunctie" in regels
    assert "Pt: ° 12/03/1968, M" in regels
    assert "STOP-BANG 7/8 (S T O P A N G) | ESS 14/24 | BMI 33,1 | Hals 43 cm" in regels
    assert "Klachten: snurken, apneus geobserveerd, nycturie, slaperig achter stuur" in regels
    assert "CV: HT (therapieresistent), VKF | DM2" in regels
    assert "Eerder: PG 2021, AHI 22 | CPAP/MRA: nee" in regels
    assert "Verwijzer: dr. An Voorbeeld, RIZIV 1-23456-78-901" in regels
    assert "ZEERUNIEKENAAM" not in r["tekst"] and "68031212345" not in r["tekst"], "patiëntnaam of rijksregisternummer in de kopie"
    assert "\t" not in r["tekst"] and r["lengte"] <= 1000 and r["ingekort"] is False


def test_kopieertekst_frans_engels_decimaal_en_afkortingen():
    fr = _kopie("fr", dict(VOORBEELD))["tekst"]
    assert "Demandé: PSG" in fr and "somnolence au volant" in fr and "IMC 33,1" in fr and "INAMI 1-23456-78-901" in fr
    en = _kopie("en", dict(VOORBEELD))["tekst"]
    assert "Requested: PSG" in en and "BMI 33.1" in en
    de = _kopie("de", dict(VOORBEELD))["tekst"]
    assert "BMI 33,1" in de and "Angefragt: PSG" in de


def test_kopieertekst_inkorten_met_de_echte_velden():
    d = dict(VOORBEELD, medicatie="bisoprolol 5 mg, " * 80, vraagstelling="Uitgebreide vraagstelling met veel context. " * 30)
    r = _kopie("nl", d, 600)
    assert r["ingekort"] and r["lengte"] <= 600, r["lengte"]
    assert r["tekst"].endswith("(volledige brief als PDF beschikbaar)")
    for kern in ("Gevraagd: PSG", "STOP-BANG 7/8", "ESS 14/24", "BMI 33,1", "Vraag: ", "Verwijzer: dr. An Voorbeeld"):
        assert kern in r["tekst"], kern
    assert r["verwijderd"][0] in ("roken", "alcohol"), "prioriteit 4 valt eerst"


def test_pdf_volgt_de_secties_en_draagt_formulierversie_en_url():
    ctx = _v8()
    ctx.eval("var window = globalThis; var self = globalThis; var navigator = {userAgent: 'v8'};"
             "var document = {createElement: function(){return {getContext: function(){return null}, style: {}}},"
             " createElementNS: function(){return {}}}; var atob = function(s){return s}; var btoa = function(s){return s};")
    ctx.eval((ROOT / "vendor" / "jspdf.umd.min.js").read_text(encoding="utf-8"))
    ctx.eval((ROOT / "static" / "js" / "pdf.js").read_text(encoding="utf-8"))
    nl = json.loads((ROOT / "i18n" / "nl.json").read_text(encoding="utf-8"))
    model = {"kop": "AANVRAAG SLAAPONDERZOEK – Slaapkliniek AZORG",
             "secties": [{"titel": "Verwijzer", "regels": [{"label": "Naam", "waarde": "dr. An Voorbeeld"}, {"label": "RIZIV-nummer", "waarde": "1-23456-78-901"}]},
                         {"titel": "Klinische gegevens", "regels": [{"label": "Lengte / gewicht / BMI / halsomtrek en nog een lang label", "waarde": "178 cm"},
                                                                    {"label": "Cardiovasculaire comorbiditeit", "waarde": ""}]},
                         {"titel": "Lege sectie", "regels": []}],
             "vrij": [{"titel": "Vraagstelling", "tekst": "Vermoeden OSAS. " * 40}, {"titel": "Keuzehulp", "tekst": "Suggestie: polygrafie (STOP-BANG 7 ≥ 5)."}],
             "verwijzerNaam": "dr. An Voorbeeld", "versie": "2026-10-a", "url": "https://slaapstudie.be/nl/"}
    ctx.eval("var I18N = " + json.dumps(nl) + "; var t = function(k){ return I18N[k] || k; }; var MODEL = " + json.dumps(model) + ";")
    uit = json.loads(ctx.eval("JSON.stringify(globalThis.Pdf.maak(MODEL, t, {jsPDF: window.jspdf.jsPDF, nietOpslaan: true, geefUitvoer: true, vandaag: '2026-10-02T10:00:00'}))"))
    assert uit["naam"] == "verwijsbrief_slaapkliniek_20261002.pdf" and "Voorbeeld" not in uit["naam"]
    pdf = uit["uitvoer"]
    assert pdf.startswith("%PDF-")
    assert "2026-10-a" in pdf, "formulierversie in de voettekst"
    assert "slaapstudie.be/nl/" in pdf, "portaal-URL in de voettekst"
    assert "Lege sectie" not in pdf


def test_geen_mailroute_of_smtp_in_de_code(dist):
    """De site verstuurt niets: geen mailto met inhoud, geen e-mailformulier, geen SMTP."""
    verboden = [r"mailto:[^\"'\s>]*[?&](subject|body)=", r"\bsmtp\b", r"nodemailer", r"sendmail", r"<form[^>]+action="]
    bestanden = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".html", ".json", ".conf", ".yml", ".sh"}
                 and not any(deel in p.parts for deel in ("vendor", ".venv-claude", ".git", "dist", "node_modules", "videos"))
                 and p.name != "test_build.py"]
    bestanden += list(dist.rglob("*.html"))
    for p in bestanden:
        tekst = p.read_text(encoding="utf-8", errors="replace")
        for patroon in verboden:
            assert not re.search(patroon, tekst, re.I), f"{p}: {patroon}"


def test_ehealthbox_blok_verborgen_tot_geconfigureerd(dist, tmp_path):
    for lang in LANGS:
        html = (dist / lang / "aanvraag" / "index.html").read_text(encoding="utf-8")
        assert 'id="ehealthbox"' not in html and "KBO | RIZIV" not in html and "&lt;" + "KBO" not in html, lang
        assert 'id="bezorgen"' in html

    def half(werk):      # actief maar zonder nummer: blijft verborgen
        f = werk / "config" / "site.json"; d = json.loads(f.read_text(encoding="utf-8"))
        d["ehealthbox"]["actief"] = True
        f.write_text(json.dumps(d), encoding="utf-8")
    d1 = bouw_kopie(tmp_path / "half", half)
    assert 'id="ehealthbox"' not in (d1 / "nl" / "aanvraag" / "index.html").read_text(encoding="utf-8")

    def vol(werk):
        f = werk / "config" / "site.json"; d = json.loads(f.read_text(encoding="utf-8"))
        d["ehealthbox"].update({"actief": True, "type": "KBO", "nummer": "0123456789", "kwaliteit": "HOSPITAL"})
        f.write_text(json.dumps(d), encoding="utf-8")
    d2 = bouw_kopie(tmp_path / "vol", vol)
    html = (d2 / "fr" / "aanvraag" / "index.html").read_text(encoding="utf-8")
    assert 'id="ehealthbox"' in html
    for waarde in ("KBO", "0123456789", "HOSPITAL", "Slaapkliniek"):
        assert f'data-kopieer="{waarde}"' in html, waarde
    assert "Le secrétariat contactera le patient" in html


def test_domeinen_nginx_en_canonical(dist):
    site = _site()
    conf = (ROOT / "nginx" / "default.conf").read_text(encoding="utf-8")
    assert re.search(r"slaapstudie\.be\s+nl;", conf) and re.search(r"etudedusommeil\.be\s+fr;", conf)
    assert "if ($start_taal) { return 302 /$start_taal/; }" in conf
    assert "server_name verwijzers.slaapkliniek.be slaapstudie.be etudedusommeil.be _;" in conf
    assert "return 301 https://slaapstudie.be$request_uri;" in conf and "return 301 https://etudedusommeil.be$request_uri;" in conf
    assert "return 301 https://slaapstudie.be/nl$request_uri;" in conf and "return 301 https://etudedusommeil.be/fr$request_uri;" in conf
    assert "absolute_redirect off;" in conf, "achter de proxy moet de Location relatief zijn (anders http://)"
    assert 'if ($http_x_forwarded_proto = "http") { return 301 https://$host$request_uri; }' in conf
    assert 'location ~ "^/(aanvraag|consult)(/|$)"' in conf
    for d in ("slaapstudie.eu", "slaapstudie.com", "www.slaapstudie.be", "etudedusommeil.eu", "etudedusommeil.com", "www.etudedusommeil.be"):
        assert d in conf, d
    # de domeinen in nginx zijn die uit site.json
    assert site["domeinen"]["nl"] == "https://slaapstudie.be" and site["domeinen"]["fr"] == "https://etudedusommeil.be"
    for lang, basis in (("nl", "https://slaapstudie.be"), ("fr", "https://etudedusommeil.be"), ("en", site["domeinen"]["standaard"]), ("de", site["domeinen"]["standaard"])):
        for pad in ("", "aanvraag/", "consult/"):
            html = (dist / lang / pad / "index.html").read_text(encoding="utf-8")
            assert f'<link rel="canonical" href="{basis}/{lang}/{pad}">' in html, (lang, pad)
            assert f'hreflang="fr" href="https://etudedusommeil.be/fr/{pad}"' in html


def test_terug_link_gaat_rechtstreeks_naar_slaapkliniek(dist):
    html = (dist / "nl" / "index.html").read_text(encoding="utf-8")
    assert 'class="terug" href="https://slaapkliniek.be/"' in html
    assert "slaapkliniek.be/start" not in html


def test_drukwerk_qr_bestaat_voor_elk_drukwerkdomein():
    site = _site()
    for taal in ("nl", "fr"):
        naam = "qr_" + site["domeinen"][taal].split("//")[1].replace(".", "_")
        for ext in ("svg", "pdf", "eps", "png"):
            f = ROOT / "drukwerk" / f"{naam}.{ext}"
            assert f.exists() and f.stat().st_size > 500, f
        svg = (ROOT / "drukwerk" / f"{naam}.svg").read_text(encoding="utf-8")
        assert 'width="330"' in svg and 'height="330"' in svg, "versie 2 (25 modules) + stille zone 4 → 33 modules × 10"

