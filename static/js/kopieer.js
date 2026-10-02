/* kopieer.js — de verwijsbrief als compacte platte tekst voor het Consult-veld "indicatie / reden
   van verwijzing". Pure functies (genereerTekst, fragmenten, inkorten) plus een kleine UI-laag.
   Het klembord is lokaal: er wordt niets verstuurd. Naam en rijksregisternummer van de patiënt
   komen er nooit in (kopie_label null in config/velden.json). */
(function (root) {
  'use strict';

  var ZONDER_DUBBELPUNT = { ess: 1, stopbang: 1, decimaal: 1, cm: 1, spatie: 1 };
  var ALLEEN_LABEL = '\u0001';

  function leeg(x) { return x === null || x === undefined || x === '' || (Array.isArray(x) && x.length === 0); }

  /** Getal als tekst: decimale komma in nl/fr/de, punt in en. */
  function getalTekst(n, taal, decimalen) {
    if (leeg(n) || !isFinite(Number(n))) return '';
    var s = decimalen === undefined ? String(Number(n)) : Number(n).toFixed(decimalen);
    return taal === 'en' ? s : s.replace('.', ',');
  }

  function datumKort(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ''));
    return m ? m[3] + '/' + m[2] + '/' + m[1] : String(iso || '');
  }

  function vindOptie(veld, waarde) {
    var o = veld.opties || [];
    for (var i = 0; i < o.length; i++) if (String(o[i].waarde) === String(waarde)) return o[i];
    return null;
  }

  function optieKopie(veld, waarde, t) {
    var o = vindOptie(veld, waarde);
    if (!o) return String(waarde);
    if (o.kopie_key) return t(o.kopie_key);
    if (o.label !== undefined) return String(o.label);
    var s = t(o.label_key);
    return s.charAt(0).toLowerCase() + s.slice(1);
  }

  function schoon(s) { return String(s).replace(/[\t\r\n]+/g, ' ').replace(/ {2,}/g, ' ').trim(); }

  function waardeTekst(veld, data, def, t, taal) {
    var v = data[veld.id], f = veld.kopie_formaat;
    var perId = {};
    def.velden.forEach(function (x) { perId[x.id] = x; });
    var toel = veld.kopie_met && !leeg(data[veld.kopie_met]) ? schoon(data[veld.kopie_met]) : '';

    if (f === 'geboortedatum') return leeg(v) ? '' : '° ' + datumKort(v);
    if (f === 'decimaal') return leeg(v) ? '' : getalTekst(v, taal, 1);
    if (f === 'cm') return leeg(v) ? '' : getalTekst(v, taal) + ' cm';
    if (f === 'ess') return leeg(v) ? '' : v + '/24';
    if (f === 'stopbang') {
      if (leeg(v)) return '';
      var letters = def.velden.filter(function (x) { return x.groep === 'stopbang' && data[x.id] === 'ja'; })
        .map(function (x) { return String(x.letter).toUpperCase(); });
      return v + '/8' + (letters.length ? ' (' + letters.join(' ') + ')' : '');
    }
    if (f === 'indien_ja') return v === 'ja' ? ALLEEN_LABEL : '';
    if (f === 'niet_standaard') {
      if (leeg(v) || (v === veld.standaard && !toel)) return '';
      return optieKopie(veld, v, t) + (toel ? ' (' + toel + ')' : '');
    }
    if (f === 'eerder') {
      if (v === 'nee') return t('kopie.nee');
      if (v !== 'ja') return '';
      var delen = [];
      if (!leeg(data.eerder_type) && perId.eerder_type) delen.push(optieKopie(perId.eerder_type, data.eerder_type, t));
      if (!leeg(data.eerder_datum)) delen.push(schoon(data.eerder_datum));
      var s = delen.join(' ') || t('kopie.ja');
      if (!leeg(data.eerder_ahi)) s += ', ' + t('kopie.ahi') + ' ' + getalTekst(data.eerder_ahi, taal);
      return s;
    }
    switch (veld.type) {
      case 'getal': return getalTekst(v, taal);
      case 'berekend': return leeg(v) ? '' : getalTekst(v, taal);
      case 'keuze': return leeg(v) ? '' : optieKopie(veld, v, t) + (toel ? ' (' + toel + ')' : '');
      case 'ja_nee': return leeg(v) ? '' : t(v === 'ja' ? 'kopie.ja' : 'kopie.nee') + (v === 'ja' && toel ? ' (' + toel + ')' : '');
      case 'meerkeuze':
        var lijst = (v || []).filter(function (x) { return x !== veld.exclusief; });
        if (!lijst.length) return (v || []).indexOf(veld.exclusief) !== -1 ? t('js.pdf_geen') : '';
        return lijst.map(function (x) { return optieKopie(veld, x, t); }).join(', ');
      default: return leeg(v) ? '' : schoon(v);
    }
  }

  function maakTekst(label, waarde, formaat) {
    if (waarde === '') return label;
    if (label === '') return waarde;
    return label + (ZONDER_DUBBELPUNT[formaat] ? ' ' : ': ') + waarde;
  }

  /** Eén fragment per ingevuld veld dat in de kopie hoort: {id, regel, prio, label, waarde, tekst, ...}. */
  function fragmenten(data, def, t, taal) {
    var uit = [];
    def.velden.forEach(function (veld, i) {
      if (veld.kopie_label === null || veld.kopie_label === undefined) return;
      var w = waardeTekst(veld, data, def, t, taal);
      if (w === '') return;
      var label = veld.kopie_label === '' ? '' : t(veld.kopie_label);
      var waarde = w === ALLEEN_LABEL ? '' : w;
      uit.push({ id: veld.id, regel: veld.kopie_regel, prio: veld.kopie_prioriteit, label: label, waarde: waarde,
                 formaat: veld.kopie_formaat, tekst: maakTekst(label, waarde, veld.kopie_formaat), inkortbaar: !!veld.inkortbaar,
                 volgorde: veld.kopie_volgorde === undefined ? 100 + i : veld.kopie_volgorde });
    });
    return uit;
  }

  function bouw(frags, def, t, kop) {
    var regels = [kop];
    (def.kopie_regels || []).forEach(function (r) {
      var fs = frags.filter(function (f) { return f.regel === r.id; }).sort(function (a, b) { return a.volgorde - b.volgorde; });
      if (!fs.length) return;
      var lijn = fs.map(function (f) { return f.tekst; }).join(r.scheiding || ' | ');
      regels.push(r.prefix_key ? t(r.prefix_key) + ': ' + lijn : lijn);
    });
    return regels.join('\n');
  }

  /**
   * Past de fragmenten in `max` tekens: eerst vallen de velden met de hoogste kopie_prioriteit
   * (prioriteit 1 valt nooit), daarna worden inkortbare vrije teksten afgekapt met "…".
   * `lengteVan(frags)` geeft de lengte van de opgebouwde tekst. Geeft {frags, ingekort, verwijderd}.
   */
  function inkorten(frags, max, lengteVan, opties) {
    opties = opties || {};
    var werk = frags.slice(), verwijderd = [], ingekort = false;
    var reserve = opties.suffixLengte || 0, maxVrij = opties.maxVrij || 160;
    function teLang() { return lengteVan(werk) + (ingekort ? reserve : 0) > max; }
    while (teLang()) {
      var idx = -1;
      for (var i = 0; i < werk.length; i++) if (werk[i].prio > 1 && (idx === -1 || werk[i].prio >= werk[idx].prio)) idx = i;
      if (idx === -1) break;
      verwijderd.push(werk[idx].id); werk.splice(idx, 1); ingekort = true;
    }
    if (teLang()) {
      werk = werk.map(function (f) {
        if (!f.inkortbaar || f.waarde.length <= maxVrij) return f;
        var kort = f.waarde.slice(0, Math.max(1, maxVrij - 1)).replace(/\s+$/, '') + '…';
        ingekort = true;
        return { id: f.id, regel: f.regel, prio: f.prio, label: f.label, waarde: kort, formaat: f.formaat,
                 tekst: maakTekst(f.label, kort, f.formaat), inkortbaar: true, volgorde: f.volgorde };
      });
    }
    return { frags: werk, ingekort: ingekort, verwijderd: verwijderd };
  }

  /** opties: {t, max, maxVrij, kliniek}. Geeft {tekst, lengte, ingekort, verwijderd}. */
  function genereerTekst(data, def, taal, opties) {
    var t = opties.t;
    var kop = t('kopie.kop') + (opties.kliniek ? ' – ' + opties.kliniek : '') + ' [' + t('kopie.form') + ' ' + def.versie + ']';
    var suffix = t('kopie.pdf_beschikbaar');
    var alle = fragmenten(data, def, t, taal);
    var r = inkorten(alle, opties.max || 1000, function (fs) { return bouw(fs, def, t, kop).length; },
                     { maxVrij: opties.maxVrij, suffixLengte: suffix.length + 1 });
    var tekst = bouw(r.frags, def, t, kop);
    if (r.ingekort) tekst += '\n' + suffix;
    return { tekst: tekst, lengte: tekst.length, ingekort: r.ingekort, verwijderd: r.verwijderd };
  }

  // ── UI: klembord met terugval op selecteren (geen document.execCommand) ──────────────────
  function naarKlembord(tekst, gelukt, mislukt) {
    var nav = root.navigator;
    if (nav && nav.clipboard && typeof nav.clipboard.writeText === 'function') nav.clipboard.writeText(tekst).then(gelukt, mislukt);
    else mislukt();
  }

  function bindUI(t) {
    var knop = document.getElementById('knop_kopieer'), vak = document.getElementById('kopie_voorbeeld'), melding = document.getElementById('kopie_melding');
    if (knop && vak) knop.addEventListener('click', function () {
      naarKlembord(vak.value,
        function () { if (melding) melding.textContent = t('kopie.gekopieerd'); },
        function () { vak.focus(); vak.select(); if (melding) melding.textContent = t('kopie.fallback'); });
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-kopieer]'), function (b) {
      var oorspronkelijk = b.textContent;
      b.addEventListener('click', function () {
        naarKlembord(b.getAttribute('data-kopieer'),
          function () { b.textContent = b.getAttribute('data-gekopieerd') || oorspronkelijk; setTimeout(function () { b.textContent = oorspronkelijk; }, 1600); },
          function () {
            var bron = b.previousElementSibling;
            if (bron && root.getSelection) { var bereik = document.createRange(); bereik.selectNodeContents(bron); var sel = root.getSelection(); sel.removeAllRanges(); sel.addRange(bereik); }
          });
      });
    });
  }

  var Kopieer = { genereerTekst: genereerTekst, fragmenten: fragmenten, inkorten: inkorten, bouw: bouw, getalTekst: getalTekst,
                  datumKort: datumKort, optieKopie: optieKopie, vindOptie: vindOptie, bindUI: bindUI };
  if (typeof module !== 'undefined' && module.exports) module.exports = Kopieer;
  root.Kopieer = Kopieer;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
