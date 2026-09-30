# v0.1.0 — 2026-09-30 — eerste versie

Statische verwijzerssite: info PG/PSG met keuzehulp, verwijsbrief-formulier met
ESS, STOP-BANG (afgeleide items overschrijfbaar), BMI en keuzehulp, PDF in de
browser (jsPDF 2.5.2, vendored, MIT), stappenplan Nexuzhealth Consult met
terugvaloptie. NL/FR/EN/DE via `build.py` (Jinja2 × `i18n/*.json`); strikte CSP
(`connect-src 'none'`, `form-action 'none'`), geen opslag, geen trackers, geen
externe CDN's. Tests: `tests/test_build.py` (randvoorwaarden op `dist/`) en
`tests/test_scores.js` (browser, Node, V8). Placeholders in `config/site.json`
(campusadressen, dienstnaam Consult, contact) worden verborgen tot ze ingevuld zijn.
