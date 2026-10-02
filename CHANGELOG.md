# v0.2.0 — 2026-10-02 — kopieertekst, velden uit config, conventielabels, eHealthBox-route, drukwerkdomeinen

**Kopieer als tekst.** Naast de PDF maakt het formulier een compacte platte tekst voor het
Consult-veld "indicatie / reden van verwijzing": één gegeven per regel, alleen ingevulde velden,
afkortingen per taal, decimale komma in NL/FR/DE en punt in EN, live voorbeeld met tekenteller.
Naam en rijksregisternummer van de patiënt staan er nooit in. Past de tekst niet in
`kopie.max_tekens` (site.json, standaard 1000), dan vallen eerst de velden met de hoogste
`kopie_prioriteit`, daarna worden Medicatie en Vraag ingekort met "…" en volgt de regel
"(volledige brief als PDF beschikbaar)"; prioriteit 1 valt nooit. Klembord via
`navigator.clipboard`, met selecteren + Ctrl+C als terugval (geen `execCommand`).

**Velden uit `config/velden.json`.** `build.py` rendert het formulier uit de velddefinitie en
controleert haar (types, secties, i18n-sleutels, verwijzingen); `form.js`, `pdf.js` en `kopieer.js`
lezen dezelfde definitie. Een gewoon veld toevoegen of wijzigen vraagt geen template- of
JS-wijziging; berekende velden (BMI, ESS, STOP-BANG) blijven code. Nieuwe velden: slaperigheid
achter het stuur, beroepschauffeur/veiligheidsfunctie, eerder slaaponderzoek (type, jaar, AHI),
CPAP/MRA, cardiovasculaire comorbiditeit apart, diabetes type 2, roken, alcohol. De STOP-vragen
S/T/O/P zijn nu ja/nee (de score verschijnt pas als ze beantwoord zijn). Formulierversie
`2026-10-a` staat in de PDF-voettekst en in de kopieertekst.

**Conventie-klaar.** Velden met `"conventie": true` dragen het label "conventie" (tooltip:
vermoedelijk vereist in de nieuwe slaapapneuconventie) en tellen mee in "x van y
conventiegegevens ingevuld". Niets blokkeert; `conventie_definitief` in site.json wisselt de tooltip.

**Hoe bezorgt u de aanvraag?** Blok onder het formulier met Consult (PDF of kopieertekst),
eHealthBox naar het secretariaat (alleen zichtbaar als `ehealthbox.actief` én de identificatie is
ingevuld, met kopieerknop per waarde) en telefoon. De site verstuurt zelf niets: geen e-mailformulier,
geen `mailto:` met inhoud, geen SMTP (test).

**Domeinen.** `slaapstudie.be` en `etudedusommeil.be` serveren de site zelf (root → `/nl/` resp.
`/fr/`), met canonical per taal uit `domeinen` in site.json; www-, .eu- en .com-varianten
verwijzen met 301 naar het .be-domein van hun taal. `verwijzers.slaapkliniek.be` blijft werken.
De link "Naar slaapkliniek.be" gaat rechtstreeks naar de site, niet meer naar de tegelpagina.

PDF: secties volgen `velden.json`, lege conventievelden tonen "-", kop in huisstijlrood.

# v0.1.0 — 2026-09-30 — eerste versie

Statische verwijzerssite: info PG/PSG met keuzehulp, verwijsbrief-formulier met
ESS, STOP-BANG (afgeleide items overschrijfbaar), BMI en keuzehulp, PDF in de
browser (jsPDF 2.5.2, vendored, MIT), stappenplan Nexuzhealth Consult met
terugvaloptie. NL/FR/EN/DE via `build.py` (Jinja2 × `i18n/*.json`); strikte CSP
(`connect-src 'none'`, `form-action 'none'`), geen opslag, geen trackers, geen
externe CDN's. Tests: `tests/test_build.py` (randvoorwaarden op `dist/`) en
`tests/test_scores.js` (browser, Node, V8). Placeholders in `config/site.json`
(campusadressen, dienstnaam Consult, contact) worden verborgen tot ze ingevuld zijn.
