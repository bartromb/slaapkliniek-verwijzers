# slaapkliniek-verwijzers

**Verwijsportaal slaapkliniek.be → Nexuzhealth Consult**
Repo: `bartromb/slaapkliniek-verwijzers` · los van YASAFlaskified · concept september 2026 · **gebouwd 30-09-2026 (v0.1.0)**

---

## 1. Doel

Een publieke website **"Voor verwijzers"** die huisartsen en andere artsen vlot begeleidt naar een aanvraag voor **polygrafie (PG)** of **polysomnografie (PSG)** in de Slaapkliniek AZORG, op de verschillende campussen.

De afspraak zelf wordt **niet** op deze site geboekt, maar in **Nexuzhealth Consult**, het gratis portaal van nexuzhealth voor externe zorgverleners. Daar logt de arts in met itsme of eID, zoekt de patiënt, kiest de dienst en een tijdslot, en voegt een verwijsbrief toe. De afspraak staat dan rechtstreeks in de KWS-agenda.

Deze site is dus een **doorgeefluik** met drie taken:

1. **Informeren:** wanneer PG en wanneer PSG, welke campus wat doet, hoe het verloopt.
2. **Een gestructureerde verwijsbrief** laten invullen, waarvan **in de browser** een PDF wordt gemaakt.
3. **Doorsturen naar Consult**, met een duidelijk stappenplan.

## 2. Architectuurkeuze: statische site, aparte repo

Omdat er geen enkele server-side verwerking nodig is, wordt dit een **volledig statische site**: HTML, CSS en JS, geserveerd door een minimale `nginx:alpine`-container.

| Waarom | |
|---|---|
| **Geen backend = geen patiëntdata op de server** | Er is technisch geen endpoint dat data kan ontvangen. Het GDPR-risico is zo goed als nul. |
| **Los van YASAFlaskified** | Geen koppeling met de scoringspipeline, eigen release-cyclus, geen risico dat een bug in de een de ander raakt. |
| **Minimaal aanvalsoppervlak** | Geen Python, geen databank, geen sessies. |
| **Eenvoudig te hosten** | Kan naast YASAFlaskified op de Hetzner-server, of later op AZORG-infrastructuur, zonder aanpassingen. |

**Build-stap:** geen, of hooguit een klein Python-script dat de HTML per taal genereert uit templates en JSON (zie §7). Geen Node-toolchain, geen bundler, geen frameworks.

## 3. Harde randvoorwaarden (niet onderhandelbaar)

| Regel | Waarom |
|---|---|
| **Geen patiëntdata verlaten de browser.** Geen `fetch`, XHR, formulier-POST, WebSocket of beacon met formulierinhoud. | Anders wordt de site een verwerker van gezondheidsdata. |
| **Geen `localStorage`, `sessionStorage`, IndexedDB of cookies** voor formulierinhoud. | Gedeelde pc's in praktijken. |
| **Geen analytics of trackers**, ook niet "privacyvriendelijke". | Dezelfde reden, en het vertrouwen van de verwijzers. |
| **Geen externe CDN's, fonts of scripts.** Alles, inclusief jsPDF, zit in `vendor/`, met licentiebestand. | CSP, beschikbaarheid, geen lekken naar derden. |
| **Geen nexuzhealth-logo's of -huisstijl.** Alleen tekstlinks naar hun publieke URL's. | Geen imitatie van een andere organisatie. |
| **Geen iframe van Consult**, geen SSO-poging, niet automatisch invullen. | Dat kan niet en mag niet. |
| **Geen inline scripts of styles.** | Strikte CSP. |

## 4. Repo-structuur

```
slaapkliniek-verwijzers/
├── CLAUDE.md                  # dit bestand
├── README.md                  # doel, lokaal draaien, deploy
├── LICENSE                    # BSD-3 (consistent met psgscoring/YASAFlaskified)
├── CHANGELOG.md
├── config/
│   └── site.json              # campussen, contact, URL's, drempels keuzehulp
├── i18n/
│   ├── nl.json
│   ├── fr.json
│   ├── en.json
│   └── de.json
├── templates/                 # Jinja2-templates (enkel gebruikt bij build)
│   ├── base.html
│   ├── index.html
│   ├── aanvraag.html
│   └── consult.html
├── static/
│   ├── css/verwijzers.css
│   ├── js/
│   │   ├── scores.js          # ESS, STOP-BANG, BMI — pure functies, getest
│   │   ├── form.js            # formulierlogica, validatie, keuzehulp
│   │   └── pdf.js             # verwijsbrief-PDF met jsPDF
│   └── img/
├── vendor/
│   ├── jspdf.umd.min.js
│   └── jspdf.LICENSE
├── build.py                   # rendert templates × talen → dist/
├── tests/
│   ├── test_scores.html       # draait scores.js-tests in de browser (test_scores.js: ook Node/V8)
│   └── test_build.py          # checks: geen ontbrekende i18n-keys, geen inline <script>, geen externe URL's
├── nginx/
│   ├── default.conf           # locations, no-store op /*/aanvraag/
│   └── security-headers.conf  # CSP en overige headers (geïncludeerd op twee niveaus)
├── Dockerfile                 # build-stage python:3.11-slim → nginx:alpine
├── docker-compose.yml
└── .github/workflows/ci.yml   # build + tests bij elke push
```

`dist/` wordt **niet** gecommit (zet het in `.gitignore`).

## 5. Pagina's en URL's

Output van `build.py` per taal:

| URL | Inhoud |
|---|---|
| `/nl/`, `/fr/`, `/en/`, `/de/` | Info en keuzehulp PG/PSG, overzicht van de campussen, CTA's |
| `/<taal>/aanvraag/` | Formulier en PDF-generator |
| `/<taal>/consult/` | Stappenplan Consult en terugvaloptie |
| `/` | Doorverwijzing naar `/nl/`. Browsertaal-detectie mag, maar via JS zonder cookie. |

Taalwissel is een link naar dezelfde pagina in een andere taal. Een ingevuld formulier gaat daarbij verloren, dus toon een waarschuwing als het formulier al data bevat (`beforeunload`).

### Hosting

**Beslist: subdomein `verwijzers.slaapkliniek.be`**, als aparte container achter Nginx Proxy Manager. De site draait op de root (`base_path` = `/`). De landingspagina van slaapkliniek.be (in de YASAFlaskified-repo) heeft een tegel "Onderzoek aanvragen" die naar `https://verwijzers.slaapkliniek.be/<taal>/` linkt. Geef deze site in de header een link terug naar `https://slaapkliniek.be/start`.

DNS (Gandi): een `A`-record `verwijzers` → `65.108.230.243`. In NPM: een Proxy Host `verwijzers.slaapkliniek.be` → container `verwijzers:80`, met SSL (Let's Encrypt), Force SSL, HSTS en HTTP/2 aan.

## 6. Gebruikersflow

```
verwijzers.slaapkliniek.be
   │
   ├── [1] Info: PG of PSG? · campussen · wachttijden · contact
   │
   ├── [2] Verwijsbrief-formulier (client-side)
   │        └── "Maak verwijsbrief (PDF)" → download in de browser
   │
   └── [3] "Afspraak boeken in Nexuzhealth Consult"
            ├── knop → Consult login (nieuw tabblad)
            ├── knop → Consult account aanvragen
            ├── stappenplan: patiënt zoeken → Afspraken → Nieuwe afspraak
            │   → AZORG → dienst Slaapkliniek (PG of PSG, campus) → slot
            │   → indicatie invullen → PDF als bijlage → bevestigen
            └── terugvaloptie zonder Consult: telefoon secretariaat / eHealthBox
```

## 7. Configuratie (`config/site.json`)

Alles wat verandert, staat hier. Waarden tussen `<>` zijn placeholders die Bart invult. `build.py` verbergt secties met lege waarden.

```json
{
  "base_path": "/",
  "consult": {
    "login_url": "https://www.nexuzhealth.com/nl/nexuzhealth-consult",
    "account_url": "https://www.nexuzhealth.com/nl/nexuzhealth-consult",
    "deeplink_slaapkliniek": null,
    "dienstnaam": "<exacte dienstnaam zoals zichtbaar in Consult>"
  },
  "campussen": [
    { "id": "wetteren",    "naam": "Campus Wetteren",    "pg": true, "psg": true, "adres": "<...>", "wachttijd_weken": null },
    { "id": "moorselbaan", "naam": "Campus Moorselbaan", "pg": true, "psg": true, "adres": "<...>", "wachttijd_weken": null }
  ],
  "contact": {
    "secretariaat_tel": "<...>",
    "ehealthbox": "<...>",
    "email_algemeen": "<niet voor patiëntdata>"
  },
  "keuzehulp": {
    "stopbang_hoge_pretest": 5,
    "comorbiditeit_naar_psg": ["hartfalen", "cva", "copd", "neuromusculair", "opioiden", "andere_slaapstoornis"]
  }
}
```

Als `consult.deeplink_slaapkliniek` gezet is, wordt die de primaire knop.

## 8. Verwijsbrief-formulier

### Velden

**Verwijzer:** naam, RIZIV-nummer (formaat `1-23456-78-901`, validatie), praktijkadres, telefoon.

**Patiënt:** naam, geboortedatum, geslacht. Het rijksregisternummer is **optioneel**, met de hint "de patiënt zoekt u in Consult op rijksregisternummer".

**Gevraagd onderzoek:** Polygrafie / PSG / "Slaaparts beslist". Voorkeurcampus: uit `campussen`, of "Geen voorkeur".

**Urgentie:** Normaal / Verhoogd (beroepschauffeur, recent ongeval, zwangerschap, preoperatief) + vrij tekstveld.

**Klinisch:**
- Klachten (checkboxes): snurken, geobserveerde apneus, slaperigheid overdag, nachtelijke dyspneu, nycturie, ochtendhoofdpijn, niet-herstellende slaap, slapeloosheid, rusteloze benen, parasomnie
- Lengte en gewicht → BMI automatisch berekend
- Halsomtrek (cm)
- **Epworth Sleepiness Scale:** 8 items (0–3), totaal automatisch berekend
- **STOP-BANG:** 8 items, automatisch berekend. Een deel wordt afgeleid (BMI > 35, leeftijd > 50, halsomtrek > 40 cm, man), maar blijft overschrijfbaar.
- Comorbiditeit: hartfalen, voorkamerfibrillatie, CVA/TIA, COPD, neuromusculaire aandoening, opioïdgebruik, chronische nierinsufficiëntie, therapieresistente hypertensie
- Huidige medicatie (vrij tekstveld)
- Eerder slaaponderzoek of CPAP? (ja/nee + tekst)
- Vraagstelling (vrij tekstveld, verplicht)

### Keuzehulp PG of PSG (alleen informatief)

- STOP-BANG ≥ drempel **en** geen enkele comorbiditeit uit `comorbiditeit_naar_psg` → suggestie **polygrafie**.
- Anders → suggestie **PSG**.
- Toon altijd: *"De slaaparts beoordeelt elke aanvraag en kan het type onderzoek aanpassen."*

### PDF (`pdf.js`)

- Knop "Maak verwijsbrief (PDF)" → jsPDF in de browser → download als `verwijsbrief_slaapkliniek_<YYYYMMDD>.pdf`. De bestandsnaam bevat **geen** patiëntnaam.
- Layout: A4, kop "Aanvraag slaaponderzoek — Slaapkliniek AZORG", gestructureerde secties, ESS- en STOP-BANG-totalen met itemscores, BMI, en onderaan de verwijzer met datum en plaats voor handtekening.
- Na de download verschijnt de volgende stap: *"Voeg deze PDF toe als bijlage bij uw afspraak in Nexuzhealth Consult"* → knop naar `/<taal>/consult/`.
- Knop "Formulier wissen".

Validatie gebeurt client-side. Verplichte velden: verwijzer (naam en RIZIV), patiëntnaam, geboortedatum, gevraagd onderzoek en vraagstelling.

## 9. Talen

- NL (primair), FR, EN, DE, in `i18n/*.json` met platte keys (`"aanvraag.titel": "..."`).
- `build.py` rendert elke template in elke taal naar `dist/<taal>/`.
- JS-strings (validatiemeldingen, PDF-teksten) krijgt de pagina mee via `<script type="application/json" id="i18n">`. Dat is data, geen script, dus compatibel met de CSP.
- `test_build.py` faalt als er een key in `nl.json` ontbreekt in een andere taal.
- ⚠️ Gebruik in Python geen variabele `t` die een vertaalfunctie `t()` overschaduwt (bekende valkuil uit YASAFlaskified).

## 10. Security (`nginx/default.conf`)

```
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'" always;
add_header Referrer-Policy "no-referrer" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Cache-Control "no-store" always;   # minstens op /*/aanvraag/
```

`connect-src 'none'` en `form-action 'none'` dwingen technisch af dat de formulierdata de browser niet verlaten. HTTPS en HSTS regelt Nginx Proxy Manager. De Nginx-access-logs bevatten alleen paden, nooit formulierdata (die worden niet verstuurd).

## 11. Design

- Rustig en professioneel, in de huisstijl van slaapkliniek.be (navy `#1A3A8F`). Systeemfonts, geen webfonts van derden.
- Mobile-first, want veel huisartsen werken op een tablet. Moet werken op 375 px breedte.
- Toegankelijkheid: labels bij alle velden, toetsenbordnavigatie, voldoende contrast.
- Voetnoot op elke pagina: *"Er worden via deze website geen gegevens naar onze server verzonden of opgeslagen."*

## 12. Deploy

Lokaal:

```bash
python3 build.py && python3 -m http.server -d dist 8080
```

Productie (Hetzner, naast YASAFlaskified, eigen map):

```bash
# eenmalig
ssh root@dedodedodo.be "mkdir -p /data/verwijzers && cd /data/verwijzers && git clone https://github.com/bartromb/slaapkliniek-verwijzers.git ."

# update
ssh root@dedodedodo.be "cd /data/verwijzers && git pull && docker compose build --no-cache && docker compose up -d"
```

De container (servicenaam `verwijzers`) publiceert geen poort naar buiten. Hij hangt aan hetzelfde Docker-netwerk als Nginx Proxy Manager (`external: true` in `docker-compose.yml`, netwerknaam nakijken met `docker network ls`), en NPM koppelt `verwijzers.slaapkliniek.be` eraan (zie §5). De `Dockerfile` draait `build.py` in een build-stage (`python:3.11-slim`) en kopieert `dist/` naar `nginx:alpine`, zodat er geen Python in de runtime-image zit.

## 13. Buiten scope (later)

- Koppeling YASAFlaskified-verslag → KWS via de XML-import (application identifier van nexuzhealth + Mirth-kanaal bij AZORG-IT). Hoort in de YASAFlaskified-repo.
- Accounts of login voor verwijzers.
- Server-side opslag van aanvragen.

## 14. Acceptatiecriteria

- [ ] `python3 build.py` genereert alle pagina's in NL/FR/EN/DE zonder ontbrekende keys.
- [ ] De CI (`.github/workflows/ci.yml`) draait build en tests, en faalt bij inline `<script>`, `<style>` of `http(s)://`-verwijzingen naar externe hosts in `dist/`, behalve de toegestane Consult-links.
- [ ] De netwerktab toont **nul** requests met formulierinhoud (formulier invullen, PDF maken, netwerklog nakijken).
- [ ] De browserconsole toont geen CSP-schendingen.
- [ ] De tests in `scores.js` slagen (ESS, STOP-BANG met afgeleide items, BMI, keuzehulp).
- [ ] De PDF opent correct in Acrobat en in de browser, en de bestandsnaam bevat geen patiëntnaam.
- [ ] Lege placeholders in `site.json` worden netjes verborgen.
- [ ] Bruikbaar op 375 px breedte en volledig bedienbaar met het toetsenbord.
- [ ] `README.md` bevat lokaal draaien en deploy, `CHANGELOG.md` heeft een entry v0.1.0.

## 15. Open vragen voor Bart / AZORG-IT

1. Zijn de slaapkliniek-agenda's (PG en PSG, per campus) al opengezet voor boeking via Nexuzhealth Consult? **Zonder dat werkt stap 3 niet.**
2. Wat is de exacte dienstnaam in Consult?
3. Bestaat er een deep-link van nexuzhealth naar het boekscherm van een specifieke dienst?
4. Welke campussen doen PG en welke doen PSG, en wat zijn de actuele wachttijden?
5. Is een verplichte vragenlijst per afspraaktype in KWS mogelijk, als aanvulling op de PDF?

## 16. Beslissingen bij het bouwen (30-09-2026)

- `build.py --check` controleert i18n-pariteit en placeholders zonder te schrijven; de versie komt
  uit de eerste kop van `CHANGELOG.md`.
- Placeholders zijn waarden die leeg zijn of met `<` beginnen (`build.py:leeg`).
- De keuzehulp staat in `scores.js:keuzehulp` en wordt door `tests/test_scores.js` getoetst op de
  drempel (≥ is inclusief) en op de lijst `comorbiditeit_naar_psg`; voorkamerfibrillatie en
  nierinsufficiëntie staan bewust NIET in die lijst (spec §7).
- Afgeleide STOP-BANG-items volgen BMI/leeftijd/hals/geslacht tot de arts ze zelf aanklikt
  (`data-handmatig`); "Formulier wissen" zet dat terug.
- RIZIV: `1-23456-78-901` of elf losse cijfers (worden genormaliseerd); andere vormen zijn fout.
- De PDF gebruikt Helvetica (WinAnsi); tekens buiten die set (≥ → ·) worden vervangen
  (`pdf.js:ascii`). Bestandsnaam `<prefix>_<YYYYMMDD>.pdf`, prefix per taal, nooit een naam.
- JS-strings gaan als `<script type="application/json">` mee (data, geen script); de test op
  inline scripts laat precies dat type toe.
- `nginx add_header` wordt niet geërfd zodra een location er zelf een zet: de headers staan in
  `security-headers.conf` en worden op server-niveau én in de aanvraag-location geïncludeerd.
- Het NPM-netwerk heet per installatie anders: `NPM_NETWORK` in `.env` (zie `.env.example`).
