/* form.js — formulierlogica: berekeningen, validatie, keuzehulp, PDF-knop, wissen, beforeunload.
   Alles blijft in de browser: geen fetch/XHR, geen opslag, geen cookie. */
(function () {
  'use strict';
  var S = window.Scores, P = window.Pdf;
  var form = document.getElementById('verwijsbrief');
  if (!form || !S || !P) return;

  var I18N = JSON.parse(document.getElementById('i18n').textContent);
  var SITE = JSON.parse(document.getElementById('site').textContent);
  var melding = document.getElementById('melding');
  var volgende = document.getElementById('volgende');
  var vuil = false;

  function t(key, params) {
    var s = I18N[key] !== undefined ? I18N[key] : key;
    if (params) Object.keys(params).forEach(function (k) { s = s.split('{' + k + '}').join(String(params[k])); });
    return s;
  }
  function $(id) { return document.getElementById(id); }
  function val(id) { var el = $(id); return el ? String(el.value || '').trim() : ''; }
  function radio(naam) { var el = form.querySelector('input[name="' + naam + '"]:checked'); return el ? el.value : ''; }
  function checks(naam) { return Array.prototype.map.call(form.querySelectorAll('input[name="' + naam + '"]:checked'), function (el) { return el.value; }); }
  function toon(tekst, ok) { melding.textContent = tekst; melding.className = 'melding' + (ok ? ' ok' : ''); melding.hidden = false; melding.focus && melding.focus(); }
  function verberg() { melding.hidden = true; melding.textContent = ''; }

  // ── berekeningen ──────────────────────────────────────────────────────────
  function essItems() {
    var items = [];
    for (var i = 1; i <= 8; i++) { var v = radio('ess_' + i); items.push(v === '' ? null : Number(v)); }
    return items;
  }
  function stopbangItems() {
    var o = {};
    S.SB_ITEMS.forEach(function (k) { var el = form.querySelector('input[name="sb_' + k + '"]'); o[k] = !!(el && el.checked); });
    return o;
  }
  function herbereken() {
    var b = S.bmi(val('lengte'), val('gewicht'));
    $('bmi').value = b === null ? '—' : String(b);
    $('bmi').textContent = $('bmi').value;

    var ess = S.essTotaal(essItems());
    $('ess_totaal').textContent = ess === null ? '—' : String(ess);
    var interp = S.essInterpretatie(ess);
    $('ess_interpretatie').textContent = interp ? '— ' + t('js.ess_interpretatie_' + interp) : '';

    var afgeleid = S.stopbangAfgeleid({ bmi: b, leeftijd: S.leeftijd(val('patient_geboortedatum')), hals: val('hals'), geslacht: radio('patient_geslacht') });
    ['b', 'a', 'n', 'g'].forEach(function (k) {
      var el = form.querySelector('input[name="sb_' + k + '"]');
      if (el && el.dataset.handmatig !== '1') el.checked = afgeleid[k];
    });
    var sb = S.stopbangTotaal(stopbangItems());
    $('sb_totaal').textContent = String(sb);

    var keuze = S.keuzehulp({ stopbang: sb, comorbiditeiten: checks('com'), drempel: SITE.keuzehulp.stopbang_hoge_pretest, naarPsg: SITE.keuzehulp.comorbiditeit_naar_psg });
    var tekst;
    if (keuze.reden === 'comorbiditeit') tekst = t('js.keuze_psg_com');
    else if (keuze.reden === 'hoog') tekst = t('js.keuze_pg', { score: sb, drempel: SITE.keuzehulp.stopbang_hoge_pretest });
    else if (keuze.reden === 'laag') tekst = t('js.keuze_psg_laag', { score: sb, drempel: SITE.keuzehulp.stopbang_hoge_pretest });
    else tekst = t('js.keuze_onvolledig');
    $('keuzehulp_tekst').textContent = tekst;
    return { bmi: b, ess: ess, essInterpretatie: interp, stopbang: sb, keuzehulpTekst: tekst };
  }

  // ── validatie ─────────────────────────────────────────────────────────────
  function valideer() {
    var fouten = [], ontbreekt = [];
    Array.prototype.forEach.call(form.querySelectorAll('.ongeldig'), function (el) { el.classList.remove('ongeldig'); });
    Array.prototype.forEach.call(form.querySelectorAll('[required]'), function (el) {
      if (String(el.value || '').trim() === '') { ontbreekt.push(el.dataset.label || el.name); el.classList.add('ongeldig'); }
    });
    if (radio('onderzoek') === '') {
      var eerste = form.querySelector('input[name="onderzoek"]');
      ontbreekt.push(eerste.dataset.label || 'onderzoek');
    }
    if (ontbreekt.length) fouten.push(t('js.val_verplicht', { velden: ontbreekt.join(', ') }));
    var riziv = val('verwijzer_riziv');
    if (riziv !== '' && !S.rizivGeldig(riziv)) { fouten.push(t('js.val_riziv')); $('verwijzer_riziv').classList.add('ongeldig'); }
    var gd = val('patient_geboortedatum');
    if (gd !== '' && !S.geboortedatumGeldig(gd)) { fouten.push(t('js.val_geboortedatum')); $('patient_geboortedatum').classList.add('ongeldig'); }
    return fouten;
  }

  // ── gegevens voor de PDF ──────────────────────────────────────────────────
  function labelVan(naam, waarde) {
    var el = form.querySelector('input[name="' + naam + '"][value="' + waarde + '"]');
    return el && el.parentNode ? el.parentNode.textContent.trim() : waarde;
  }
  function verzamel(berekend) {
    var sbItems = stopbangItems();
    var geslacht = radio('patient_geslacht');
    var campusId = val('campus');
    return {
      verwijzer: { naam: val('verwijzer_naam'), riziv: S.rizivNormaliseer(val('verwijzer_riziv')) || val('verwijzer_riziv'), adres: val('verwijzer_adres'), tel: val('verwijzer_tel') },
      patient: { naam: val('patient_naam'), geboortedatum: val('patient_geboortedatum'), geslacht: geslacht,
                 geslachtLabel: geslacht ? labelVan('patient_geslacht', geslacht) : '', rrn: val('patient_rrn') },
      onderzoek: { code: radio('onderzoek'), label: labelVan('onderzoek', radio('onderzoek')),
                   campus: campusId, campusLabel: campusId ? (SITE.campussen[campusId] || campusId) : t('aanvraag.campus_geen') },
      urgentie: { code: radio('urgentie'), label: labelVan('urgentie', radio('urgentie')), toelichting: val('urgentie_toelichting') },
      klachten: checks('klacht').map(function (k) { return t('aanvraag.klacht_' + k); }),
      lengte: val('lengte'), gewicht: val('gewicht'), bmi: berekend.bmi, hals: val('hals'),
      ess: { totaal: berekend.ess, items: essItems(), interpretatie: berekend.essInterpretatie ? t('js.ess_interpretatie_' + berekend.essInterpretatie) : '' },
      stopbang: { totaal: berekend.stopbang, items: sbItems,
                  itemsTekst: S.SB_ITEMS.map(function (k) { return k.toUpperCase() + (sbItems[k] ? '+' : '-'); }).join(' ') },
      comorbiditeit: checks('com').map(function (k) { return t('aanvraag.com_' + k); }),
      medicatie: val('medicatie'),
      eerder: { ja: radio('eerder') === 'ja', toelichting: val('eerder_toelichting') },
      vraagstelling: val('vraagstelling'),
      keuzehulpTekst: berekend.keuzehulpTekst
    };
  }

  // ── gebeurtenissen ────────────────────────────────────────────────────────
  form.addEventListener('input', function () { vuil = true; herbereken(); });
  form.addEventListener('change', function (e) {
    vuil = true;
    if (e.target && e.target.classList && e.target.classList.contains('afgeleid')) e.target.dataset.handmatig = '1';
    herbereken();
  });
  form.addEventListener('submit', function (e) { e.preventDefault(); });

  $('knop_pdf').addEventListener('click', function () {
    var berekend = herbereken();
    var fouten = valideer();
    if (fouten.length) { volgende.hidden = true; toon(fouten.join(' '), false); return; }
    try {
      P.maak(verzamel(berekend), t);
    } catch (err) {
      toon(String(err && err.message ? err.message : err), false);
      return;
    }
    toon(t('js.val_ok'), true);
    volgende.hidden = false;
    volgende.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  $('knop_wissen').addEventListener('click', function () {
    if (vuil && !window.confirm(t('js.wissen_bevestig'))) return;
    form.reset();
    Array.prototype.forEach.call(form.querySelectorAll('[data-handmatig]'), function (el) { delete el.dataset.handmatig; });
    Array.prototype.forEach.call(form.querySelectorAll('.ongeldig'), function (el) { el.classList.remove('ongeldig'); });
    vuil = false; volgende.hidden = true; verberg(); herbereken();
  });

  window.addEventListener('beforeunload', function (e) {
    if (!vuil) return;
    e.preventDefault();
    e.returnValue = t('js.verlaten');
    return e.returnValue;
  });
  Array.prototype.forEach.call(document.querySelectorAll('a[data-taalwissel]'), function (a) {
    a.addEventListener('click', function (e) { if (vuil && !window.confirm(t('js.verlaten'))) e.preventDefault(); });
  });

  herbereken();
})();
