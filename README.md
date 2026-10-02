# slaapkliniek-verwijzers

Verwijsportaal **slaapstudie.be** (NL), **etudedusommeil.be** (FR) en **verwijzers.slaapkliniek.be**: een volledig statische website die huisartsen en
andere artsen begeleidt naar een aanvraag voor polygrafie (PG) of polysomnografie (PSG) in de
Slaapkliniek. De arts vult een gestructureerde verwijsbrief in, maakt er **in de browser** een PDF
van (jsPDF, vendored) en boekt de afspraak zelf in **Nexuzhealth Consult**. De site is een
doorgeefluik: er is geen backend en er verlaten geen patiëntgegevens de browser — technisch
afgedwongen met `connect-src 'none'` en `form-action 'none'` in de CSP.

Ontwerp en randvoorwaarden: [`CLAUDE.md`](CLAUDE.md). Los van
[YASAFlaskified](https://github.com/bartromb/YASAFlaskified); de landingspagina van
slaapkliniek.be linkt hierheen met de tegel "Onderzoek aanvragen".

## Demo

Filmpje (± 1 min 45, zonder geluid, fictieve gegevens; NL/FR/EN/DE) van het hele proces — info, verwijsbrief
invullen, PDF maken, stap naar Consult: op de infopagina van de site
(`/<taal>/#video`) en als assets bij de
[GitHub-release v0.1.0](https://github.com/bartromb/slaapkliniek-verwijzers/releases/tag/v0.1.0),
samen met de voorbeeld-PDF. Opgenomen met `tools/record_demo.py` (Playwright + ffmpeg tegen de
live site); opnieuw opnemen:

```bash
.venv/bin/pip install playwright imageio-ffmpeg pymupdf
for l in nl fr en de; do .venv/bin/python tools/record_demo.py --lang $l --chrome <pad naar chrome> --out videos/; done
```

## Formulier aanpassen (`config/velden.json`)

Het formulier, de PDF en de kopieertekst komen uit één velddefinitie. Een veld toevoegen:

```json
{ "id": "nieuw_veld", "type": "ja_nee", "label_key": "veld.nieuw_veld", "verplicht": false,
  "conventie": true, "kopie_label": "kopie.nieuw_veld", "kopie_prioriteit": 2,
  "kopie_regel": "klachten", "sectie": "klinisch", "weergave": "radio",
  "opties": [{"waarde": "ja", "label_key": "veld.ja"}, {"waarde": "nee", "label_key": "veld.nee"}] }
```

plus de labels in `i18n/*.json`. `python3 build.py --check` meldt elke fout (onbekend type, ontbrekende
sleutel, onbekende sectie of kopie-regel). Types: `tekst`, `getal`, `datum`, `keuze`, `meerkeuze`,
`ja_nee`, `berekend`, `vrije_tekst`. Verhoog `versie` bij elke inhoudelijke wijziging; ze staat in de
PDF-voettekst en in de kopieertekst. Zodra de conventietekst definitief is: `conventie`-vlaggen
nalopen en `conventie_definitief: true` in `config/site.json`.

Kopieertekst: `kopie_label` (i18n-sleutel van de afkorting; `null` = nooit in de kopie, zoals
patiëntnaam en rijksregisternummer), `kopie_prioriteit` (1 = valt nooit weg), `kopie_regel` (op welke
regel), `kopie.max_tekens` in `site.json`. eHealthBox: `ehealthbox` in `site.json`; het blok verschijnt
pas als `actief` op `true` staat en type en nummer ingevuld zijn.

## Drukwerk

QR-codes voor pennen en zakkaart staan in [`drukwerk/`](drukwerk/) (SVG, PDF, EPS, PNG), met richtlijnen
voor de drukker. Ze verwijzen naar `slaapstudie.be` en `etudedusommeil.be`; `tools/maak_qr.py` maakt ze
opnieuw uit `config/site.json`.

## Structuur

- `config/site.json` — campussen, contact, Consult-URL's en -dienstnaam, drempels keuzehulp,
  toegestane externe hosts. Waarden die leeg zijn of met `<` beginnen zijn placeholders: de
  bijbehorende secties worden verborgen tot ze ingevuld zijn.
- `i18n/{nl,fr,en,de}.json` — platte sleutels; `nl.json` is de referentie, de andere talen
  moeten exact dezelfde sleutels dragen (test).
- `templates/` — Jinja2 (`base`, `index`, `aanvraag`, `consult`, `root`), alleen bij de build.
- `config/velden.json` — velddefinitie van het formulier (zie hierboven).
- `static/js/scores.js` — zuivere rekenfuncties (BMI, leeftijd, ESS, STOP-BANG, keuzehulp,
  RIZIV); `kopieer.js` — kopieertekst (pure functies + klembord); `form.js` — formulier op basis
  van `velden.json`; `pdf.js` — verwijsbrief-PDF; `lang.js` — taalkeuze op `/`.
- `vendor/jspdf.umd.min.js` — jsPDF 2.5.2 (MIT, `vendor/jspdf.LICENSE`).
- `build.py` — rendert templates × talen naar `dist/` (niet gecommit).
- `tests/test_build.py` — randvoorwaarden op `dist/`; `tests/test_scores.js` en
  `tests/test_kopieer.js` — rekenfuncties en kopieertekst (browser via `tests/test_*.html`, Node,
  of V8 vanuit pytest).
- `nginx/` — CSP en overige headers; `Dockerfile` — build-stage (Python) + `nginx:alpine`.

## Lokaal draaien

```bash
python3 -m venv .venv && .venv/bin/pip install "jinja2>=3.1" pytest mini-racer
.venv/bin/python build.py && python3 -m http.server -d dist 8080     # http://localhost:8080/nl/
.venv/bin/pytest -q                                                   # + node tests/test_scores.js
```

Handmatige controle (acceptatiecriteria): vul het formulier in, maak de PDF, open de netwerktab —
er mag **geen enkel** verzoek met formulierinhoud staan — en de console mag geen CSP-schending
tonen (met de nginx-container; `http.server` stuurt geen CSP-headers).

## Deploy (Hetzner, naast YASAFlaskified, eigen map)

```bash
# eenmalig
ssh root@dedodedodo.be "mkdir -p /data/verwijzers && cd /data/verwijzers && git clone https://github.com/bartromb/slaapkliniek-verwijzers.git . && cp .env.example .env"
# NPM_NETWORK in .env zetten op het netwerk van Nginx Proxy Manager (docker network ls)

# update
ssh root@dedodedodo.be "cd /data/verwijzers && git pull && docker compose build --no-cache && docker compose up -d"
```

De container `verwijzers` publiceert geen poort; hij hangt aan het NPM-netwerk. In Nginx Proxy
Manager: Proxy Host `verwijzers.slaapkliniek.be` → `verwijzers:80`, SSL (Let's Encrypt), Force SSL,
HSTS, HTTP/2. DNS (Gandi): `A`-record `verwijzers` → het serveradres.

## Open vragen (zie CLAUDE.md §15)

Consult-agenda's opengezet, exacte dienstnaam in Consult, deeplink, campussen en wachttijden,
verplichte vragenlijst in KWS. Tot die tijd staan placeholders in `config/site.json`.
