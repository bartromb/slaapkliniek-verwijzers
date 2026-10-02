# QR-codes voor drukwerk

| bestand | inhoud | komt uit op |
|---|---|---|
| `qr_slaapstudie_be.*` | `HTTPS://SLAAPSTUDIE.BE` | https://slaapstudie.be/nl/ |
| `qr_etudedusommeil_be.*` | `HTTPS://ETUDEDUSOMMEIL.BE` | https://etudedusommeil.be/fr/ |

Formaten: **SVG, PDF, EPS** (vector, voor de drukker) en **PNG** (1188 × 1188 px, voor schermgebruik).
Gemaakt met `tools/maak_qr.py` uit `config/site.json` → `domeinen`; opnieuw genereren na een
domeinwijziging: `.venv/bin/pip install segno && .venv/bin/python tools/maak_qr.py`.

## Eigenschappen

- QR-versie 2: 25 × 25 modules, de kleinste code die deze URL's draagt. De URL staat in hoofdletters
  (domeinnamen zijn niet hoofdlettergevoelig) zodat de compacte alfanumerieke modus volstaat.
- Foutcorrectie Q: tot 25 % van de code mag beschadigd of onleesbaar zijn (krassen op een pen).
- Stille zone van 4 modules rondom zit in de bestanden; snijd die niet weg.

## Voor de drukker

| toepassing | minimale zijde (incl. witte rand) | modulegrootte |
|---|---|---|
| pen (tampondruk of laser) | 10 mm | ≥ 0,30 mm |
| zakkaart, visitekaart | 15 mm | ≥ 0,45 mm |
| affiche, flyer (scannen op armlengte) | 25 mm | ≥ 0,75 mm |

- Donker op licht: zwart (of AZORG-donkergrijs `#1F1F1F`) op wit of zeer licht. Niet inverteren, geen
  rood op wit op kleine formaten (minder contrast voor oudere camera's).
- Niet uitrekken: de code blijft vierkant. Geen logo in het midden op pen-formaat.
- Op een ronde pen: de code in de lengterichting plaatsen, niet rond de kromming wikkelen.
- Vraag een proefdruk en scan hem met twee toestellen (iPhone en Android) vóór de oplage.

De codes verwijzen naar de root van het domein; de site kiest daar de taal. Er zit geen tracking in.
