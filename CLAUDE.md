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


---

# Addendum: kopieertekst, conventie-klare velden en eHealthBox-route

**Opdracht voor Claude Code** · repo `bartromb/slaapkliniek-verwijzers` · aanvulling op `CLAUDE.md` · oktober 2026

Lees eerst `CLAUDE.md`. Alle harde randvoorwaarden daarin blijven gelden: geen data naar de server, geen opslag in de browser, strikte CSP, geen externe scripts.

---

## 1. Waarom

1. **Kopieertekst.** Mogelijk laat Nexuzhealth Consult (of de configuratie bij AZORG) geen PDF-bijlage toe bij een afspraak. De huisarts moet de inhoud van de verwijsbrief dan als **tekst** kunnen plakken in het vrije veld "indicatie / reden van verwijzing". Tekst in KWS is bovendien doorzoekbaar en meteen zichtbaar, dus deze functie komt er **altijd**, ook naast de PDF.
2. **Conventie-klaar.** De gevraagde gegevens (ESS, STOP-BANG, BMI, comorbiditeit, enz.) worden **vermoedelijk** gevraagd in de nieuwe RIZIV-slaapapneuconventie vanaf 1/1/2027. De definitieve criteria zijn nog niet gekend. Daarom moet de veldenlijst **configureerbaar** zijn, zodat ze aangepast kan worden zonder codewijziging zodra de conventietekst er is.

## 2. Velden: configureerbaar maken

Verplaats de definitie van de formuliervelden van de templates naar **`config/velden.json`**. `build.py` rendert het formulier daaruit; `form.js`, `pdf.js` en `kopieer.js` lezen dezelfde definitie (meegegeven als `<script type="application/json" id="velden">`).

Per veld:

```json
{
  "id": "ess_totaal",
  "type": "berekend",
  "label_key": "veld.ess_totaal",
  "verplicht": false,
  "conventie": true,
  "kopie_label": "ESS",
  "kopie_prioriteit": 1,
  "sectie": "klinisch"
}
```

| Sleutel | Betekenis |
|---|---|
| `type` | `tekst`, `getal`, `datum`, `keuze`, `meerkeuze`, `ja_nee`, `berekend`, `vrije_tekst` |
| `verplicht` | client-side validatie |
| `conventie` | `true` = vermoedelijk vereist voor de conventie. Toon een klein label "conventie" naast het veld, en een teller "x van y conventiegegevens ingevuld" boven de knoppen. **Niet blokkerend.** |
| `kopie_label` | korte afkorting in de kopieertekst; `null` = niet opnemen in de kopie |
| `kopie_prioriteit` | 1 = altijd mee, hoger = eerst geschrapt als de tekst te lang wordt |
| `sectie` | groepering in formulier en PDF |

Voeg naast de velden uit `CLAUDE.md` §8 ook deze toe, allemaal met `"conventie": true` tenzij anders vermeld:

- **Slaperigheid achter het stuur / bijna-ongeval** (ja/nee)
- **Beroepschauffeur of veiligheidsfunctie** (ja/nee)
- **Eerder slaaponderzoek**: ja/nee + datum + type (PG/PSG) + AHI indien gekend
- **Eerdere of huidige CPAP / MRA**: ja/nee + toelichting
- **Cardiovasculaire comorbiditeit** apart oplijsten (hypertensie, therapieresistente hypertensie, VKF, hartfalen, CVA/TIA, coronair lijden)
- **Diabetes type 2**
- **Rookgedrag** en **alcoholgebruik** (keuze, `"conventie": false`)

Plaats bovenaan `velden.json` een **`"versie": "2026-10-a"`**. Die versie komt mee in de PDF-voettekst en in de kopieertekst, zodat je later kan zien met welke formulierversie een verwijzing is gemaakt.

⚠️ Schrijf in de UI nergens dat iets "verplicht voor de conventie" is. Gebruik "vermoedelijk vereist in de nieuwe conventie" in de tooltip, tot `config/site.json` → `"conventie_definitief": true` staat.

## 3. Kopieertekst

### UI

- Op de aanvraagpagina, naast "Maak verwijsbrief (PDF)": de knop **"Kopieer als tekst"**.
- Daaronder een **voorbeeldvak** (`<textarea readonly>`, 6–10 regels) met de gegenereerde tekst, live bijgewerkt bij elke wijziging. Toon de lengte: "312 / 1000 tekens".
- Na klikken: melding "Gekopieerd. Plak dit in Consult bij 'indicatie / reden van verwijzing'." (via `aria-live="polite"`).
- **Fallback** als `navigator.clipboard` niet beschikbaar is (oude browser, geen HTTPS): selecteer de tekst in het voorbeeldvak en toon "Druk Ctrl+C (Cmd+C)". Gebruik geen `document.execCommand('copy')`.

Het klembord is lokaal; dit verstuurt niets. De CSP (`connect-src 'none'`) blijft ongewijzigd.

### Formaat

Compact, één gegeven per regel, alleen ingevulde velden, geen lege labels. Taal = de taal van de interface. Voorbeeld (NL):

```
AANVRAAG SLAAPONDERZOEK – Slaapkliniek AZORG [form 2026-10-a]
Gevraagd: PSG | Voorkeur: Wetteren | Urgentie: verhoogd (beroepschauffeur)
Pt: ° 12/03/1968, M
STOP-BANG 6/8 (S T O P B N) | ESS 14/24 | BMI 33,1 | Hals 43 cm
Klachten: snurken, apneus geobserveerd, slaperig achter stuur, nycturie
CV: HT (therapieresistent), VKF | DM2
Eerder: PG 2021, AHI 22 | CPAP: nee
Medicatie: bisoprolol, apixaban, metformine
Vraag: OSA? Graag beoordeling, rijgeschiktheid.
Verwijzer: dr. [naam], RIZIV 1-23456-78-901
```

Regels:
- **Naam en rijksregisternummer van de patiënt komen er niet in.** De patiënt is in Consult al geselecteerd. Neem alleen geboortedatum en geslacht op, als controle.
- Afkortingen staan in de i18n-bestanden (`kopie.*`), per taal. Gebruik in FR bv. `Demandé: PSG`, `Somnolence au volant`.
- STOP-BANG toont de positieve letters tussen haakjes; ESS toont alleen het totaal (de itemscores staan in de PDF).
- Decimale komma in NL en FR, punt in EN.
- Lijnen eindigen op `\n`; geen tabs, geen opmaak, geen emoji.

### Lengtelimiet

- `config/site.json` → `"kopie": {"max_tekens": 1000}`. De echte limiet van het Consult-veld is nog onbekend (open vraag), dus kies 1000 als voorzichtige standaard.
- Is de tekst te lang, laat dan eerst de velden met de hoogste `kopie_prioriteit` vallen. Kort daarna "Medicatie" en "Vraag" in tot een vast maximum met "…". Voeg ten slotte de regel `(volledige brief als PDF beschikbaar)` toe.
- Velden met prioriteit 1 (onderzoek, STOP-BANG, ESS, BMI, vraagstelling, verwijzer) worden nooit geschrapt.

## 4. Derde route: eHealthBox naar het secretariaat

Naast boeken in Consult (met PDF-bijlage of kopieertekst) krijgt de verwijzer een derde route: de verwijsbrief **vanuit de eigen dossiersoftware via de eHealthBox** naar de slaapkliniek sturen. De eHealthBox is het Belgische, end-to-end versleutelde kanaal tussen zorgverleners. Huisartsen gebruiken het dagelijks en het is het aangewezen, GDPR-conforme kanaal voor medische gegevens.

**De site verstuurt zelf niets.** Ze toont alleen hoe het moet en het adres.

### UI

Op de aanvraagpagina komt na de knoppen een blok **"Hoe bezorgt u de aanvraag?"** met drie opties:

1. **Afspraak boeken in Nexuzhealth Consult**, met de PDF als bijlage of de kopieertekst in het indicatieveld (link naar `/<taal>/consult/`).
2. **Via eHealthBox naar het secretariaat**:
   - Download de PDF (of kopieer de tekst).
   - Verstuur ze vanuit uw dossiersoftware naar de eHealthBox van de Slaapkliniek AZORG.
   - Toon de identificatie uit de config, met een knop **"Kopieer"** per waarde (bv. type: `KBO` / `RIZIV` / `EHP`, nummer, kwaliteit, eventueel naam van de dienst).
   - Vermeld: "Het secretariaat neemt contact op met de patiënt voor een afspraak."
3. **Telefonisch**: het nummer van het secretariaat (bestaande terugvaloptie).

Toon optie 2 **alleen** als `config/site.json` → `ehealthbox.actief` op `true` staat **en** de identificatie is ingevuld. Anders verberg je het blok volledig. Toon nooit een placeholder.

### Configuratie (`config/site.json`)

Vervang het bestaande veld `contact.ehealthbox` door:

```json
"ehealthbox": {
  "actief": false,
  "type": "<KBO | RIZIV | EHP>",
  "nummer": "<...>",
  "kwaliteit": "<bv. HOSPITAL>",
  "dienst": "Slaapkliniek",
  "toelichting_key": "ehealthbox.toelichting"
}
```

`actief` gaat pas op `true` als AZORG-IT de box of de routering naar de slaapkliniek heeft bevestigd, **en** vaststaat wie de box dagelijks leest.

### Expliciet niet bouwen

- **Geen** formulier dat de verwijsbrief per e-mail verstuurt (ook niet "versleuteld" of via SMTP op de server). Daarmee wordt de site een verwerker van gezondheidsgegevens.
- **Geen** `mailto:`-link met de inhoud van de brief in het onderwerp of de body. Gewone e-mail is niet end-to-end versleuteld en is niet aangewezen voor medische gegevens.
- **Geen** integratie met eHealth-webservices vanuit de site. Versturen gebeurt altijd vanuit de software van de verwijzer.

### Teksten (i18n)

- `ehealthbox.titel`: "Via eHealthBox" / "Via eHealthBox"
- `ehealthbox.toelichting`: "Versleuteld en beveiligd kanaal tussen zorgverleners, rechtstreeks vanuit uw medisch dossier." / "Canal sécurisé et chiffré entre prestataires de soins, directement depuis votre dossier médical."
- `ehealthbox.na_verzending`: "Het secretariaat neemt contact op met de patiënt voor een afspraak." / "Le secrétariat contactera le patient pour fixer un rendez-vous."

## 5. Bestanden

```
config/velden.json          # NIEUW: velddefinities + versie
static/js/kopieer.js        # NIEUW: genereren, inkorten, kopiëren (pure functies + UI-binding)
static/js/form.js           # aangepast: rendert/valideert op basis van velden.json, conventieteller
static/js/pdf.js            # aangepast: secties uit velden.json, formulierversie in voettekst
templates/aanvraag.html     # aangepast: knop, voorbeeldvak, aria-live
i18n/*.json                 # nieuwe keys: veld.*, kopie.*, conventie.*
tests/test_kopieer.html     # NIEUW
tests/test_build.py         # uitgebreid
```

Houd `kopieer.js` opgesplitst in **pure functies** (`genereerTekst(data, velden, taal)`, `inkorten(tekst, regels, max)`) en een kleine UI-laag, zodat de logica testbaar is zonder DOM.

## 6. Domeinen

Volgens de nieuwe beslissing komen op het drukwerk (pennen, zakkaart):

| Domein | Gaat naar |
|---|---|
| `slaapstudie.be` | `/nl/` |
| `etudedusommeil.be` (zonder accent) | `/fr/` |
| `verwijzers.slaapkliniek.be` | blijft werken |

- Alle domeinen wijzen naar dezelfde container. Werk dit uit in `nginx/default.conf` (redirect van de root `/` per `Host` naar de juiste taal) en in de README (DNS-records en NPM-proxyhosts voor alle domeinen).
- Canonical-URL per taal: NL → `https://slaapstudie.be/nl/…`, FR → `https://etudedusommeil.be/fr/…`. Zet die als `<link rel="canonical">`.
- Werk ook de QR-code en URL's in templates en PDF bij naar deze domeinen. Zet de domeinen in `config/site.json`, niet hardcoded.

## 7. Acceptatiecriteria

- [ ] Het formulier wordt volledig opgebouwd uit `config/velden.json`. Een veld toevoegen of wijzigen vraagt geen JS- of templatewijziging.
- [ ] De conventieteller werkt en blokkeert niets; de labels zeggen "vermoedelijk".
- [ ] "Kopieer als tekst" werkt in Chrome, Edge, Firefox en Safari. De fallback werkt zonder `navigator.clipboard`.
- [ ] De kopieertekst bevat **nooit** patiëntnaam of rijksregisternummer (testgeval).
- [ ] Inkorten respecteert `max_tekens` en de prioriteiten; prioriteit 1 blijft altijd staan (testgevallen met overlange medicatie en vraagstelling).
- [ ] NL- en FR-teksten zijn correct, met decimale komma.
- [ ] De formulierversie staat in de PDF en in de kopieertekst.
- [ ] De netwerktab toont nog steeds **nul** requests met formulierinhoud; de console toont geen CSP-schendingen.
- [ ] `slaapstudie.be/` → `/nl/` en `etudedusommeil.be/` → `/fr/`; `verwijzers.slaapkliniek.be` werkt nog.
- [ ] Het eHealthBox-blok is onzichtbaar zolang `ehealthbox.actief` op `false` staat of het nummer leeg is. Met geldige config toont het de identificatie met werkende kopieerknoppen.
- [ ] Er bestaat nergens in de code een `mailto:` met formulierinhoud, een e-mailformulier of een SMTP-configuratie (testgeval in `test_build.py`: grep op `mailto:` met body/subject, `smtp`, `nodemailer`).
- [ ] `CHANGELOG.md`: entry v0.2.0.

## 8. Open vragen (voor Bart / AZORG-IT)

1. Laat Consult een bijlage toe bij een afspraak in de AZORG-configuratie?
2. Hoeveel tekens kan het veld "indicatie / reden van verwijzing" in Consult bevatten? (→ `max_tekens`)
3. Kan KWS een verplichte vragenlijst per afspraaktype koppelen? Dan kunnen de conventievelden daar gestructureerd terechtkomen.
4. **eHealthBox:** welke box gebruikt AZORG (type, nummer, kwaliteit)? Komen berichten binnen in KWS? Kan er een aparte dienstbox komen voor de slaapkliniek, of routering via de ziekenhuisbox? Wie leest ze dagelijks? Een aparte box vraagt AZORG aan, met het eHealth-certificaat van het ziekenhuis. Tot dan blijft `ehealthbox.actief` op `false`. Een persoonlijke box van een arts (RIZIV) is geen goede oplossing op dienstniveau.
5. Zodra de conventietekst (vanaf 1/1/2027) definitief is: `velden.json` nalopen, `conventie`-vlaggen aanpassen, `conventie_definitief: true` zetten en de versie verhogen.

## 9. Beslissingen bij het bouwen van het addendum (02-10-2026, v0.2.0)

- Extra sleutels in `velden.json` naast die uit §2: `kopie_regel` (+ `kopie_regels` met scheiding en
  prefix) om gegevens op één regel te groeperen, `kopie_formaat` (geboortedatum, decimaal, cm, ess,
  stopbang, indien_ja, niet_standaard, eerder, spatie), `kopie_met` (toelichting tussen haakjes),
  `kopie_volgorde`, `inkortbaar`, `weergave`, `opties`, `toon_als`, `exclusief`, `groep`, `letter`,
  `afgeleid`, `formule`, `validatie`, `keuzehulp`, `rij`, `opties_bron`.
- "Geen JS-wijziging per veld" geldt voor gewone velden. Berekende velden (`formule`) en de
  afgeleide STOP-BANG-items gebruiken de vaste ids `lengte`, `gewicht`, `hals`,
  `patient_geboortedatum`, `patient_geslacht`; een nieuwe formule vraagt code.
- S/T/O/P zijn ja/nee-radio's (expliciet antwoord, nodig voor de conventieteller); B/A/N/G blijven
  afgeleide vinkjes. De keuzehulp geeft pas een suggestie als S/T/O/P beantwoord zijn.
- Meerkeuzevelden met `conventie` hebben een optie "Geen van deze" (`exclusief`), zodat "geen"
  expliciet kan en meetelt.
- `kopie_label` is een i18n-sleutel (`kopie.*`), `""` betekent "alleen de waarde" (geboortedatum,
  geslacht), `null` betekent "nooit in de kopie".
- De klinieknaam komt uit `site.json` → `kliniek`; de PDF-kop en de kopieertekst gebruiken dezelfde regel.
- Canonical: NL → slaapstudie.be, FR → etudedusommeil.be, EN/DE → `domeinen.standaard`
  (verwijzers.slaapkliniek.be). De nginx-config is statisch; `tests/test_build.py` bewaakt dat ze
  dezelfde domeinen draagt als `site.json`.
- Er bestaat geen QR-code in de site of de PDF; de PDF-voettekst draagt de portaal-URL per taal.
  Een QR voor drukwerk is niet gebouwd (staat niet in de acceptatiecriteria).
