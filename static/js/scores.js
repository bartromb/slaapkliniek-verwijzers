/* scores.js — zuivere rekenfuncties voor het verwijsformulier (ESS, STOP-BANG, BMI, keuzehulp).
   Geen DOM, geen netwerk, geen opslag. Getest in tests/test_scores.js (browser én Node/V8). */
(function (root) {
  'use strict';

  var SB_ITEMS = ['s', 't', 'o', 'p', 'b', 'a', 'n', 'g'];

  function getal(x) {
    if (x === null || x === undefined || x === '') return null;
    var n = Number(x);
    return isFinite(n) ? n : null;
  }

  /** BMI op één decimaal, of null als lengte/gewicht ontbreken of onzinnig zijn. */
  function bmi(lengteCm, gewichtKg) {
    var l = getal(lengteCm), g = getal(gewichtKg);
    if (l === null || g === null || l < 50 || l > 300 || g <= 0) return null;
    var m = l / 100;
    return Math.round(g / (m * m) * 10) / 10;
  }

  /** Leeftijd in volle jaren op `vandaag` (Date of ISO-string), of null. */
  function leeftijd(geboortedatumIso, vandaag) {
    var g = new Date(String(geboortedatumIso) + 'T00:00:00');
    if (isNaN(g.getTime())) return null;
    var v = vandaag ? new Date(vandaag) : new Date();
    var a = v.getFullYear() - g.getFullYear();
    var m = v.getMonth() - g.getMonth();
    if (m < 0 || (m === 0 && v.getDate() < g.getDate())) a -= 1;
    return a;
  }

  /** Geboortedatum: geldige datum, in het verleden, niet vóór 1880. */
  function geboortedatumGeldig(iso, vandaag) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(iso || ''))) return false;
    var delen = iso.split('-').map(Number);
    var d = new Date(delen[0], delen[1] - 1, delen[2]);          // lokale tijd, geen UTC-verschuiving
    if (isNaN(d.getTime()) || d.getFullYear() !== delen[0] || d.getMonth() + 1 !== delen[1] || d.getDate() !== delen[2]) return false;
    var v = vandaag ? new Date(vandaag) : new Date();
    return d.getTime() < v.getTime() && d.getFullYear() >= 1880;
  }

  /** ESS-totaal (0–24) uit acht items 0–3; null zodra één item ontbreekt of ongeldig is. */
  function essTotaal(items) {
    if (!items || items.length !== 8) return null;
    var t = 0;
    for (var i = 0; i < 8; i++) {
      var n = getal(items[i]);
      if (n === null || n !== Math.floor(n) || n < 0 || n > 3) return null;
      t += n;
    }
    return t;
  }

  function essInterpretatie(totaal) {
    if (totaal === null || totaal === undefined) return null;
    return totaal <= 10 ? 'normaal' : 'verhoogd';
  }

  /** Afgeleide STOP-BANG-items (B, A, N, G) uit BMI, leeftijd, halsomtrek en geslacht. */
  function stopbangAfgeleid(p) {
    p = p || {};
    var b = getal(p.bmi), a = getal(p.leeftijd), n = getal(p.hals);
    return {
      b: b !== null && b > 35,
      a: a !== null && a > 50,
      n: n !== null && n > 40,
      g: p.geslacht === 'm'
    };
  }

  /** STOP-BANG-totaal (0–8) uit een object met booleans s,t,o,p,b,a,n,g. */
  function stopbangTotaal(items) {
    items = items || {};
    var t = 0;
    for (var i = 0; i < SB_ITEMS.length; i++) if (items[SB_ITEMS[i]]) t += 1;
    return t;
  }

  /**
   * Keuzehulp (alleen informatief): comorbiditeit uit `naarPsg` → PSG;
   * anders STOP-BANG ≥ drempel → PG; anders PSG (lage voorafkans).
   */
  function keuzehulp(p) {
    p = p || {};
    var naarPsg = p.naarPsg || [];
    var com = (p.comorbiditeiten || []).filter(function (c) { return naarPsg.indexOf(c) !== -1; });
    if (com.length) return { advies: 'psg', reden: 'comorbiditeit', comorbiditeiten: com };
    var sb = getal(p.stopbang), drempel = getal(p.drempel);
    if (sb === null || drempel === null) return { advies: null, reden: 'onvolledig' };
    if (sb >= drempel) return { advies: 'pg', reden: 'hoog' };
    return { advies: 'psg', reden: 'laag' };
  }

  /** RIZIV-nummer: 1-23456-78-901; elf losse cijfers worden genormaliseerd. Geeft de nette vorm of null. */
  function rizivNormaliseer(s) {
    var k = String(s || '').trim();
    if (/^\d-\d{5}-\d{2}-\d{3}$/.test(k)) return k;
    var cijfers = k.replace(/[\s.\-\/]/g, '');
    if (/^\d{11}$/.test(cijfers)) {
      return cijfers[0] + '-' + cijfers.slice(1, 6) + '-' + cijfers.slice(6, 8) + '-' + cijfers.slice(8, 11);
    }
    return null;
  }

  function rizivGeldig(s) { return rizivNormaliseer(s) !== null; }

  var Scores = {
    SB_ITEMS: SB_ITEMS, bmi: bmi, leeftijd: leeftijd, geboortedatumGeldig: geboortedatumGeldig,
    essTotaal: essTotaal, essInterpretatie: essInterpretatie, stopbangAfgeleid: stopbangAfgeleid,
    stopbangTotaal: stopbangTotaal, keuzehulp: keuzehulp, rizivNormaliseer: rizivNormaliseer, rizivGeldig: rizivGeldig
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = Scores;
  root.Scores = Scores;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
