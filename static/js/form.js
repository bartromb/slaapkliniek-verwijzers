/* form.js — formulierlogica op basis van config/velden.json (meegegeven als #velden): waarden lezen,
   berekeningen, zichtbaarheid (toon_als), validatie, conventieteller, keuzehulp, kopieertekst en
   PDF. Alles blijft in de browser: geen fetch/XHR, geen opslag, geen cookie.
   Gewone velden vragen geen code; berekende velden (formule bmi/ess/stopbang) en de afgeleide
   STOP-BANG-items gebruiken de vaste ids lengte, gewicht, hals, patient_geboortedatum, patient_geslacht. */
(function () {
  'use strict';
  var S = window.Scores, P = window.Pdf, K = window.Kopieer;
  var form = document.getElementById('verwijsbrief');
  if (!form || !S || !K) return;

  function lees(id) { return JSON.parse(document.getElementById(id).textContent); }
  function $(id) { return document.getElementById(id); }
  function alle(sel) { return Array.prototype.slice.call(form.querySelectorAll(sel)); }

  var I18N = lees('i18n'), SITE = lees('site'), DEF = lees('velden');
  var VELDEN = DEF.velden, perId = {};
  VELDEN.forEach(function (v) { perId[v.id] = v; });
  var melding = $('melding'), vuil = false;

  function t(key, params) {
    var s = I18N[key] !== undefined ? I18N[key] : key;
    if (params) Object.keys(params).forEach(function (k) { s = s.split('{' + k + '}').join(String(params[k])); });
    return s;
  }
  function groep(naam) { return VELDEN.filter(function (v) { return v.groep === naam; }); }
  function wrapper(v) { return form.querySelector('[data-veld="' + v.id + '"]'); }
  function zichtbaar(v) { var w = wrapper(v); return !(w && w.hidden); }
  function toon(tekst, ok) { melding.textContent = tekst; melding.className = 'melding' + (ok ? ' ok' : ''); melding.hidden = false; }
  function verberg() { melding.hidden = true; melding.textContent = ''; }

  // ── waarden ───────────────────────────────────────────────────────────────
  function ruw(v) {
    var el, r;
    switch (v.type) {
      case 'tekst': case 'vrije_tekst': case 'datum': case 'getal':
        el = $(v.id); return el ? String(el.value || '').trim() : '';
      case 'keuze':
        if (v.weergave === 'select') { el = $(v.id); return el ? el.value : ''; }
        r = form.querySelector('input[name="' + v.id + '"]:checked'); return r ? r.value : '';
      case 'ja_nee':
        if (v.weergave === 'vink') { el = $(v.id); return el && el.checked ? 'ja' : 'nee'; }
        r = form.querySelector('input[name="' + v.id + '"]:checked'); return r ? r.value : '';
      case 'meerkeuze':
        return alle('input[name="' + v.id + '"]:checked').map(function (c) { return c.value; });
      default: return null;
    }
  }

  function pasZichtbaarheidToe() {
    VELDEN.forEach(function (v) {
      if (!v.toon_als) return;
      var w = wrapper(v), bron = perId[v.toon_als.veld];
      if (w && bron) w.hidden = ruw(bron) !== v.toon_als.waarde;
    });
  }

  function verzamel() {
    var data = {};
    VELDEN.forEach(function (v) {
      if (v.type === 'berekend') return;
      data[v.id] = zichtbaar(v) ? ruw(v) : (v.type === 'meerkeuze' ? [] : '');
      // een geldig RIZIV-nummer krijgt overal dezelfde nette vorm (kopieertekst én PDF)
      if (v.validatie === 'riziv' && S.rizivNormaliseer(data[v.id])) data[v.id] = S.rizivNormaliseer(data[v.id]);
    });
    var bmi = S.bmi(data.lengte, data.gewicht);
    var afg = S.stopbangAfgeleid({ bmi: bmi, leeftijd: S.leeftijd(data.patient_geboortedatum), hals: data.hals, geslacht: data.patient_geslacht });
    VELDEN.forEach(function (v) {
      if (!v.afgeleid) return;
      var el = $(v.id);
      if (el && el.dataset.handmatig !== '1') el.checked = !!afg[v.afgeleid];
      data[v.id] = el && el.checked ? 'ja' : 'nee';
    });
    VELDEN.forEach(function (v) {
      if (v.type !== 'berekend') return;
      if (v.formule === 'bmi') data[v.id] = bmi;
      else if (v.formule === 'ess') data[v.id] = S.essTotaal(groep('ess').map(function (x) { return data[x.id] === '' ? null : Number(data[x.id]); }));
      else if (v.formule === 'stopbang') {
        var items = {}, volledig = true;
        groep('stopbang').forEach(function (x) { if (data[x.id] === '') volledig = false; items[x.letter] = data[x.id] === 'ja'; });
        data[v.id] = volledig ? S.stopbangTotaal(items) : null;
      } else data[v.id] = null;
    });
    return data;
  }

  function ingevuld(v, data) {
    var w = data[v.id];
    if (v.type === 'meerkeuze') return w.length > 0;
    return w !== '' && w !== null && w !== undefined;
  }
  function stopbangLetters(data) {
    return groep('stopbang').filter(function (x) { return data[x.id] === 'ja'; }).map(function (x) { return String(x.letter).toUpperCase(); }).join(' ');
  }
  function veldMetFormule(f) { return VELDEN.filter(function (v) { return v.formule === f; })[0]; }

  // ── herberekenen: uitvoer, keuzehulp, conventieteller, kopieertekst ──────
  function herbereken() {
    pasZichtbaarheidToe();
    var data = verzamel(), taal = SITE.lang;
    VELDEN.forEach(function (v) {
      if (v.type !== 'berekend') return;
      var el = $(v.id), toel = $(v.id + '_toelichting'), w = data[v.id];
      if (!el) return;
      if (w === null || w === undefined) { el.textContent = '—'; if (toel) toel.textContent = ''; return; }
      if (v.formule === 'bmi') el.textContent = K.getalTekst(w, taal, 1);
      else if (v.formule === 'ess') { el.textContent = w + ' / 24'; if (toel) toel.textContent = t('js.ess_interpretatie_' + S.essInterpretatie(w)); }
      else if (v.formule === 'stopbang') el.textContent = w + ' / 8';
      else el.textContent = String(w);
    });

    var sbVeld = veldMetFormule('stopbang'), sb = sbVeld ? data[sbVeld.id] : null;
    var com = [];
    VELDEN.forEach(function (v) { if (v.keuzehulp) com = com.concat(data[v.id] || []); });
    var kh = SITE.keuzehulp || {};
    var keuze = S.keuzehulp({ stopbang: sb, comorbiditeiten: com, drempel: kh.stopbang_hoge_pretest, naarPsg: kh.comorbiditeit_naar_psg });
    var khTekst;
    if (keuze.reden === 'comorbiditeit') khTekst = t('js.keuze_psg_com');
    else if (keuze.reden === 'hoog') khTekst = t('js.keuze_pg', { score: sb, drempel: kh.stopbang_hoge_pretest });
    else if (keuze.reden === 'laag') khTekst = t('js.keuze_psg_laag', { score: sb, drempel: kh.stopbang_hoge_pretest });
    else khTekst = t('js.keuze_onvolledig');
    $('keuzehulp_tekst').textContent = khTekst;

    var conv = VELDEN.filter(function (v) { return v.conventie && zichtbaar(v); });
    var teller = $('conventie_teller');
    if (teller) teller.textContent = t('conventie.teller', { x: conv.filter(function (v) { return ingevuld(v, data); }).length, y: conv.length });

    var vak = $('kopie_voorbeeld');
    if (vak) {
      var kopie = K.genereerTekst(data, DEF, taal, { t: t, max: SITE.kopie.max_tekens, maxVrij: SITE.kopie.max_vrije_tekst, kliniek: SITE.kliniek });
      vak.value = kopie.tekst;
      $('kopie_lengte').textContent = t('kopie.lengte', { n: kopie.lengte, max: SITE.kopie.max_tekens });
    }
    return { data: data, keuzehulpTekst: khTekst };
  }

  // ── validatie (alleen `verplicht` en formaatregels; conventievelden blokkeren niets) ──
  function markeer(v) { var el = $(v.id); if (el && el.classList) el.classList.add('ongeldig'); }
  function valideer(data) {
    var fouten = [], ontbreekt = [];
    alle('.ongeldig').forEach(function (el) { el.classList.remove('ongeldig'); });
    VELDEN.forEach(function (v) {
      if (!v.verplicht || !zichtbaar(v) || ingevuld(v, data)) return;
      ontbreekt.push(t(v.label_key)); markeer(v);
    });
    if (ontbreekt.length) fouten.push(t('js.val_verplicht', { velden: ontbreekt.join(', ') }));
    VELDEN.forEach(function (v) {
      if (!v.validatie || data[v.id] === '') return;
      if (v.validatie === 'riziv' && !S.rizivGeldig(data[v.id])) { fouten.push(t('js.val_riziv')); markeer(v); }
      if (v.validatie === 'geboortedatum' && !S.geboortedatumGeldig(data[v.id])) { fouten.push(t('js.val_geboortedatum')); markeer(v); }
    });
    return fouten;
  }

  // ── PDF-model: secties en regels volgen velden.json ───────────────────────
  function optieLabel(v, waarde) {
    var o = K.vindOptie(v, waarde);
    if (!o) return String(waarde);
    return o.label !== undefined ? String(o.label) : t(o.label_key);
  }
  function weergave(v, data) {
    var w = data[v.id];
    switch (v.type) {
      case 'getal': return K.getalTekst(w, SITE.lang);
      case 'keuze': return w === '' ? '' : optieLabel(v, w);
      case 'ja_nee': return w === '' ? '' : t(w === 'ja' ? 'veld.ja' : 'veld.nee');
      case 'meerkeuze': return w.map(function (x) { return optieLabel(v, x); }).join(', ');
      case 'berekend':
        if (w === null || w === undefined) return '';
        if (v.formule === 'bmi') return K.getalTekst(w, SITE.lang, 1);
        if (v.formule === 'ess') return w + '/24 (' + t('js.ess_interpretatie_' + S.essInterpretatie(w)) + ')';
        if (v.formule === 'stopbang') { var l = stopbangLetters(data); return w + '/8' + (l ? ' (' + l + ')' : ''); }
        return String(w);
      default: return String(w || '');
    }
  }
  function pdfModel(data, keuzehulpTekst) {
    var secties = [], vrij = [];
    DEF.secties.forEach(function (s) {
      var vs = VELDEN.filter(function (v) { return v.sectie === s.id && zichtbaar(v); });
      if (vs.length === 1 && vs[0].type === 'vrije_tekst') { vrij.push({ titel: t(s.label_key), tekst: data[vs[0].id] }); return; }
      var regels = [];
      vs.forEach(function (v) {
        if (v.groep === 'ess' || v.groep === 'stopbang') return;       // items staan bij het totaal
        var w = weergave(v, data);
        if (w === '' && !v.conventie && !v.verplicht) return;
        regels.push({ label: t(v.label_key), waarde: w });
        if (v.formule === 'ess' && data[v.id] !== null && data[v.id] !== undefined) {
          regels.push({ label: t('js.pdf_ess_items'), waarde: groep('ess').map(function (x, i) { return (i + 1) + ':' + data[x.id]; }).join('  ') });
        }
      });
      secties.push({ titel: t(s.label_key), regels: regels });
    });
    vrij.push({ titel: t('js.pdf_keuzehulp'), tekst: keuzehulpTekst + '\n' + t('aanvraag.keuzehulp_arts') });
    return { kop: t('kopie.kop') + ' – ' + SITE.kliniek, secties: secties, vrij: vrij,
             verwijzerNaam: data.verwijzer_naam || '', versie: DEF.versie, url: SITE.url };
  }

  // ── gebeurtenissen ────────────────────────────────────────────────────────
  form.addEventListener('input', function () { vuil = true; herbereken(); });
  form.addEventListener('change', function (e) {
    vuil = true;
    var el = e.target;
    if (el && el.classList && el.classList.contains('afgeleid')) el.dataset.handmatig = '1';
    // "geen van deze" sluit de andere opties uit, en omgekeerd
    if (el && el.type === 'checkbox' && perId[el.name] && perId[el.name].exclusief && el.checked) {
      var ex = perId[el.name].exclusief;
      alle('input[name="' + el.name + '"]').forEach(function (c) {
        if (c !== el && (el.value === ex || c.value === ex)) c.checked = false;
      });
    }
    herbereken();
  });
  form.addEventListener('submit', function (e) { e.preventDefault(); });

  $('knop_pdf').addEventListener('click', function () {
    var r = herbereken();
    var fouten = valideer(r.data);
    if (fouten.length) { toon(fouten.join(' '), false); melding.focus(); return; }
    try {
      P.maak(pdfModel(r.data, r.keuzehulpTekst), t);
    } catch (err) {
      toon(String(err && err.message ? err.message : err), false);
      return;
    }
    toon(t('js.val_ok'), true);
    var bez = $('bezorgen');
    if (bez) bez.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  $('knop_wissen').addEventListener('click', function () {
    if (vuil && !window.confirm(t('js.wissen_bevestig'))) return;
    form.reset();
    alle('[data-handmatig]').forEach(function (el) { delete el.dataset.handmatig; });
    alle('.ongeldig').forEach(function (el) { el.classList.remove('ongeldig'); });
    var km = $('kopie_melding'); if (km) km.textContent = '';
    vuil = false; verberg(); herbereken();
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

  K.bindUI(t);
  herbereken();
})();
