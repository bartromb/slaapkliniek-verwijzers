#!/usr/bin/env python3
"""build.py — rendert templates × talen naar dist/. Geen bundler, geen Node.

    python3 build.py            # schrijft dist/
    python3 build.py --check    # alleen controleren (i18n-pariteit, velddefinitie), niets schrijven

dist/<taal>/index.html, dist/<taal>/aanvraag/index.html, dist/<taal>/consult/index.html,
dist/index.html (taalkeuze + doorverwijzing), dist/static/, dist/vendor/.
Het formulier wordt opgebouwd uit config/velden.json; dezelfde definitie gaat als JSON mee naar
form.js, pdf.js en kopieer.js. Waarden in config/site.json die leeg zijn of met "<" beginnen
zijn placeholders: de bijbehorende secties worden verborgen.
"""
from __future__ import annotations
import json
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent
LANGS = ["nl", "fr", "en", "de"]
PAGINAS = {"index": "", "aanvraag": "aanvraag/", "consult": "consult/"}
DIST = ROOT / "dist"
TYPES = {"tekst", "getal", "datum", "keuze", "meerkeuze", "ja_nee", "berekend", "vrije_tekst"}
FORMULES = {"bmi", "ess", "stopbang"}
JS_I18N_PREFIXEN = ("js.", "aanvraag.", "veld.", "kopie.", "conventie.", "sectie.")


def leeg(v) -> bool:
    return v is None or (isinstance(v, str) and (v.strip() == "" or v.strip().startswith("<")))


def schoon(obj):
    """Placeholders (leeg of '<...>') worden None, recursief; booleans, lijsten en dicts blijven."""
    if isinstance(obj, dict):
        return {k: schoon(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [schoon(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    return None if leeg(obj) else obj


def versie() -> str:
    m = re.search(r"^#+\s*v?(\d+\.\d+\.\d+)", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "0.0.0"


def laad_i18n() -> dict[str, dict]:
    strings = {lang: json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGS}
    basis = set(strings["nl"])
    fouten = []
    for lang in LANGS[1:]:
        ontbreekt = sorted(basis - set(strings[lang]))
        extra = sorted(set(strings[lang]) - basis)
        if ontbreekt or extra:
            fouten.append(f"{lang}: ontbreekt {ontbreekt} extra {extra}")
    for lang in LANGS:
        lege = [k for k, v in strings[lang].items() if not isinstance(v, str) or not v.strip()]
        if lege:
            fouten.append(f"{lang}: lege waarden {lege}")
    if fouten:
        raise SystemExit("i18n-fout:\n  " + "\n  ".join(fouten))
    return strings


def laad_velden(strings_nl: dict, campussen: list) -> dict:
    """Leest en controleert config/velden.json; vult opties uit site.json in (opties_bron)."""
    d = json.loads((ROOT / "config" / "velden.json").read_text(encoding="utf-8"))
    d.pop("_toelichting", None)
    fouten = []
    if not re.fullmatch(r"\d{4}-\d{2}-[a-z]", str(d.get("versie", ""))):
        fouten.append(f"versie {d.get('versie')!r} heeft niet de vorm JJJJ-MM-x")
    secties = {s["id"] for s in d.get("secties", [])}
    regels = {r["id"] for r in d.get("kopie_regels", [])}
    ids: set[str] = set()

    def sleutel(k, waar):
        if k and k not in strings_nl:
            fouten.append(f"{waar}: i18n-sleutel {k!r} bestaat niet")

    for s in d.get("secties", []):
        sleutel(s.get("label_key"), f"sectie {s['id']}")
        sleutel(s.get("intro_key"), f"sectie {s['id']}")
    for r in d.get("kopie_regels", []):
        sleutel(r.get("prefix_key"), f"kopie_regel {r['id']}")
    for v in d.get("velden", []):
        vid = v.get("id", "?")
        if vid in ids:
            fouten.append(f"veld {vid}: id komt twee keer voor")
        ids.add(vid)
        if v.get("type") not in TYPES:
            fouten.append(f"veld {vid}: onbekend type {v.get('type')!r}")
        if v.get("sectie") not in secties:
            fouten.append(f"veld {vid}: onbekende sectie {v.get('sectie')!r}")
        sleutel(v.get("label_key"), f"veld {vid}")
        sleutel(v.get("hint_key"), f"veld {vid}")
        sleutel(v.get("leeg_key"), f"veld {vid}")
        if v.get("kopie_label") is not None:
            sleutel(v["kopie_label"], f"veld {vid} (kopie_label)")
            if v.get("kopie_regel") not in regels:
                fouten.append(f"veld {vid}: kopie_regel {v.get('kopie_regel')!r} bestaat niet")
            if not isinstance(v.get("kopie_prioriteit"), int) or v["kopie_prioriteit"] < 1:
                fouten.append(f"veld {vid}: kopie_prioriteit moet een geheel getal ≥ 1 zijn")
        if v.get("type") == "berekend" and v.get("formule") not in FORMULES:
            fouten.append(f"veld {vid}: onbekende formule {v.get('formule')!r} (nieuwe formules vragen code in scores.js/form.js)")
        if v.get("opties_bron") == "campussen":
            v["opties"] = [{"waarde": c["id"], "label": c["naam"]} for c in campussen]
        if v.get("type") in ("keuze", "meerkeuze") and not v.get("opties") and v.get("opties_bron") != "campussen":
            fouten.append(f"veld {vid}: {v['type']} zonder opties")
        if v.get("type") == "ja_nee" and v.get("weergave") != "vink" and not v.get("opties"):
            fouten.append(f"veld {vid}: ja_nee (radio) zonder opties")
        for opt in v.get("opties") or []:
            if "label" not in opt:
                sleutel(opt.get("label_key"), f"veld {vid} optie {opt.get('waarde')}")
            sleutel(opt.get("kopie_key"), f"veld {vid} optie {opt.get('waarde')}")
    for v in d.get("velden", []):
        ta = v.get("toon_als")
        if ta and ta.get("veld") not in ids:
            fouten.append(f"veld {v['id']}: toon_als verwijst naar onbekend veld {ta.get('veld')!r}")
        if v.get("kopie_met") and v["kopie_met"] not in ids:
            fouten.append(f"veld {v['id']}: kopie_met verwijst naar onbekend veld {v['kopie_met']!r}")
    if fouten:
        raise SystemExit("velden.json-fout:\n  " + "\n  ".join(fouten))
    return d


def blokken_per_sectie(velden: dict) -> list[dict]:
    """Secties met hun velden; opeenvolgende velden met dezelfde `rij` vormen één rij-blok."""
    uit = []
    for s in velden["secties"]:
        vs = [v for v in velden["velden"] if v["sectie"] == s["id"]]
        blokken: list[dict] = []
        for v in vs:
            if v.get("rij") and blokken and blokken[-1].get("rij") == v["rij"]:
                blokken[-1]["velden"].append(v)
            elif v.get("rij"):
                blokken.append({"rij": v["rij"], "velden": [v]})
            else:
                blokken.append({"rij": None, "velden": [v]})
        uit.append({**s, "blokken": blokken, "velden": vs})
    return uit


def main(argv: list[str]) -> int:
    alleen_check = "--check" in argv
    site = schoon(json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8")))
    strings = laad_i18n()
    base_path = site.get("base_path") or "/"
    if not base_path.endswith("/"):
        base_path += "/"
    campussen = [c for c in (site.get("campussen") or []) if c and c.get("naam")]
    contact = site.get("contact") or {}
    consult = site.get("consult") or {}
    domeinen = site.get("domeinen") or {}
    standaard = (domeinen.get("standaard") or site.get("site_url") or "").rstrip("/")
    canoniek = {lang: (domeinen.get(lang) or standaard).rstrip("/") for lang in LANGS}
    ehb = site.get("ehealthbox") or {}
    ehb_zichtbaar = bool(ehb.get("actief") is True and ehb.get("nummer") and ehb.get("type"))
    kopie_cfg = {"max_tekens": int((site.get("kopie") or {}).get("max_tekens") or 1000),
                 "max_vrije_tekst": int((site.get("kopie") or {}).get("max_vrije_tekst") or 160)}
    velden = laad_velden(strings["nl"], campussen)
    secties = blokken_per_sectie(velden)
    n_conventie = sum(1 for v in velden["velden"] if v.get("conventie"))
    v = versie()

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True,
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    uitvoer: dict[Path, str] = {}
    for lang in LANGS:
        s = strings[lang]

        def t(key: str, _s=s, _lang=lang) -> str:
            if key not in _s:
                raise SystemExit(f"i18n: sleutel {key!r} ontbreekt in {_lang}.json")
            return _s[key]

        js_i18n = {k: val for k, val in s.items() if k.startswith(JS_I18N_PREFIXEN)}
        js_site = {"lang": lang, "base_path": base_path, "keuzehulp": site.get("keuzehulp") or {},
                   "campussen": {c["id"]: c["naam"] for c in campussen}, "kopie": kopie_cfg,
                   "kliniek": site.get("kliniek") or s["site.merk"], "url": canoniek[lang] + base_path + lang + "/",
                   "conventie_definitief": bool(site.get("conventie_definitief"))}
        # {lang} in de Consult-URL's per taal invullen (login-portaal en accountformulier zijn meertalig)
        consult_lang = {k: (val.replace("{lang}", lang) if isinstance(val, str) else val) for k, val in consult.items()}
        for pagina, pad in PAGINAS.items():
            html = env.get_template(f"{pagina}.html").render(
                t=t, lang=lang, langs=LANGS, pagina=pagina, pagina_pad=pad, base_path=base_path,
                canoniek=canoniek, terug_url=site.get("terug_url") or base_path, versie=v,
                campussen=campussen, contact=contact, consult=consult_lang, js_i18n=js_i18n, js_site=js_site,
                secties=secties, js_velden=velden, formulierversie=velden["versie"], n_conventie=n_conventie,
                conventie_tooltip=t("conventie.tooltip_definitief" if site.get("conventie_definitief") else "conventie.tooltip"),
                ehealthbox=ehb, ehealthbox_zichtbaar=ehb_zichtbaar, kopie_cfg=kopie_cfg)
            uitvoer[DIST / lang / pad / "index.html"] = html
    uitvoer[DIST / "index.html"] = env.get_template("root.html").render(
        base_path=base_path, site_url=standaard, langs=LANGS, canoniek=canoniek, site_naam=strings["nl"]["site.naam"],
        taalnamen=[(lang, strings[lang]["site.lang_naam"]) for lang in LANGS])

    if alleen_check:
        print(f"check ok: {len(uitvoer)} pagina's, {len(strings['nl'])} sleutels × {len(LANGS)} talen, "
              f"{len(velden['velden'])} velden (formulier {velden['versie']}), v{v}")
        return 0
    if DIST.exists():
        shutil.rmtree(DIST)
    for pad, html in uitvoer.items():
        pad.parent.mkdir(parents=True, exist_ok=True)
        pad.write_text(html, encoding="utf-8")
    shutil.copytree(ROOT / "static", DIST / "static")
    shutil.copytree(ROOT / "vendor", DIST / "vendor")
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    print(f"dist/ geschreven: {len(uitvoer)} pagina's, formulier {velden['versie']}, v{v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
