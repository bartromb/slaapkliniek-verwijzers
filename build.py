#!/usr/bin/env python3
"""build.py — rendert templates × talen naar dist/. Geen bundler, geen Node.

    python3 build.py            # schrijft dist/
    python3 build.py --check    # alleen controleren (i18n-pariteit, placeholders), niets schrijven

dist/<taal>/index.html, dist/<taal>/aanvraag/index.html, dist/<taal>/consult/index.html,
dist/index.html (taalkeuze + doorverwijzing), dist/static/, dist/vendor/.
Waarden in config/site.json die leeg zijn of met "<" beginnen zijn placeholders: de
bijbehorende secties worden verborgen.
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


def leeg(v) -> bool:
    return v is None or v is False or (isinstance(v, str) and (v.strip() == "" or v.strip().startswith("<")))


def schoon(obj):
    """Placeholders (leeg of '<...>') worden None, recursief; lijsten en dicts blijven."""
    if isinstance(obj, dict):
        return {k: schoon(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [schoon(v) for v in obj]
    return None if leeg(obj) and not isinstance(obj, bool) else obj


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


def main(argv: list[str]) -> int:
    alleen_check = "--check" in argv
    site = schoon(json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8")))
    strings = laad_i18n()
    base_path = site.get("base_path") or "/"
    if not base_path.endswith("/"):
        base_path += "/"
    site_url = (site.get("site_url") or "").rstrip("/")
    campussen = [c for c in (site.get("campussen") or []) if c and c.get("naam")]
    contact = site.get("contact") or {}
    consult = site.get("consult") or {}
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

        js_i18n = {k: val for k, val in s.items() if k.startswith(("js.", "aanvraag."))}
        js_site = {"lang": lang, "base_path": base_path, "keuzehulp": site.get("keuzehulp") or {},
                   "campussen": {c["id"]: c["naam"] for c in campussen}}
        # {lang} in de Consult-URL's per taal invullen (login-portaal en accountformulier zijn meertalig)
        consult_lang = {k: (v.replace("{lang}", lang) if isinstance(v, str) else v) for k, v in consult.items()}
        for pagina, pad in PAGINAS.items():
            html = env.get_template(f"{pagina}.html").render(
                t=t, lang=lang, langs=LANGS, pagina=pagina, pagina_pad=pad, base_path=base_path,
                site_url=site_url, terug_url=site.get("terug_url") or base_path, versie=v,
                campussen=campussen, contact=contact, consult=consult_lang, js_i18n=js_i18n, js_site=js_site)
            uitvoer[DIST / lang / pad / "index.html"] = html
    uitvoer[DIST / "index.html"] = env.get_template("root.html").render(
        base_path=base_path, site_url=site_url, langs=LANGS, site_naam=strings["nl"]["site.naam"],
        taalnamen=[(lang, strings[lang]["site.lang_naam"]) for lang in LANGS])

    if alleen_check:
        print(f"check ok: {len(uitvoer)} pagina's, {len(strings['nl'])} sleutels × {len(LANGS)} talen, v{v}")
        return 0
    if DIST.exists():
        shutil.rmtree(DIST)
    for pad, html in uitvoer.items():
        pad.parent.mkdir(parents=True, exist_ok=True)
        pad.write_text(html, encoding="utf-8")
    shutil.copytree(ROOT / "static", DIST / "static")
    shutil.copytree(ROOT / "vendor", DIST / "vendor")
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    print(f"dist/ geschreven: {len(uitvoer)} pagina's, v{v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
