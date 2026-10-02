#!/usr/bin/env python3
"""tools/maak_qr.py — QR-codes voor drukwerk (pennen, zakkaart) uit config/site.json → drukwerk/.

    .venv/bin/pip install segno && .venv/bin/python tools/maak_qr.py

Per drukwerkdomein (domeinen.nl, domeinen.fr) een QR naar de root van het domein; die stuurt door
naar de juiste taal. De URL staat in HOOFDLETTERS: domeinnamen zijn niet hoofdlettergevoelig, en
hoofdletters passen in de compacte alfanumerieke QR-modus. Zo blijft de code versie 2 (25 × 25
modules) met foutcorrectie Q (25 % herstel) — de kleinst mogelijke code die ook op een pen nog
scant. Uitvoer: SVG, PDF en EPS (vector, voor de drukker) en PNG (1200 px).
"""
from __future__ import annotations
import json
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parents[1]
UIT = ROOT / "drukwerk"
RAND = 4            # stille zone in modules (QR-norm: minimaal 4)


def main() -> None:
    site = json.loads((ROOT / "config" / "site.json").read_text(encoding="utf-8"))
    UIT.mkdir(exist_ok=True)
    for taal in ("nl", "fr"):
        url = site["domeinen"][taal].rstrip("/")
        inhoud = url.upper()
        qr = segno.make(inhoud, error="q", micro=False, boost_error=True)
        naam = "qr_" + url.split("//")[1].replace(".", "_")
        qr.save(str(UIT / f"{naam}.svg"), border=RAND, scale=10, xmldecl=True, svgclass=None, lineclass=None, omitsize=False)
        qr.save(str(UIT / f"{naam}.pdf"), border=RAND, scale=10)
        qr.save(str(UIT / f"{naam}.eps"), border=RAND, scale=10)
        zijde = qr.symbol_size(border=RAND)[0]
        qr.save(str(UIT / f"{naam}.png"), border=RAND, scale=max(1, 1200 // zijde))
        print(f"{naam}: {inhoud} | versie {qr.version} ({qr.symbol_size(border=0)[0]} modules) | foutcorrectie {qr.error} | modus {qr.mode}")


if __name__ == "__main__":
    main()
