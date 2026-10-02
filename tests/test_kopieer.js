/* tests/test_kopieer.js — de pure functies van kopieer.js, met een eigen kleine velddefinitie.
   Draait in de browser (tests/test_kopieer.html), in Node (node tests/test_kopieer.js) en in V8
   via tests/test_build.py. Zet __RESULT_KOPIEER op 'OK (n checks)' of gooit bij de eerste fout. */
(function (root) {
  'use strict';
  var K = root.Kopieer || (typeof require === 'function' ? require('../static/js/kopieer.js') : null);
  if (!K) throw new Error('Kopieer niet geladen');
  var n = 0;
  function ok(c, wat) { n++; if (!c) throw new Error('FOUT ' + wat); }
  function eq(a, b, wat) { n++; if (a !== b) throw new Error('FOUT ' + wat + ': ' + JSON.stringify(a) + ' != ' + JSON.stringify(b)); }

  var T = { 'k.kop': 'AANVRAAG', 'kopie.kop': 'AANVRAAG', 'kopie.form': 'form', 'kopie.pdf_beschikbaar': '(volledige brief als PDF beschikbaar)',
            'kopie.ja': 'ja', 'kopie.nee': 'nee', 'kopie.ahi': 'AHI', 'js.pdf_geen': 'geen', 'k.gevraagd': 'Gevraagd', 'k.voorkeur': 'Voorkeur',
            'k.urgentie': 'Urgentie', 'k.pt': 'Pt', 'k.bmi': 'BMI', 'k.hals': 'Hals', 'k.ess': 'ESS', 'k.sb': 'STOP-BANG', 'k.klachten': 'Klachten',
            'k.stuur': 'slaperig achter stuur', 'k.roken': 'Roken', 'k.med': 'Medicatie', 'k.vraag': 'Vraag', 'k.verwijzer': 'Verwijzer', 'k.riziv': 'RIZIV',
            'o.pg': 'PG', 'o.psg': 'PSG', 'o.m': 'M', 'o.normaal': 'normaal', 'o.verhoogd': 'verhoogd', 'l.snurken': 'Snurken', 'l.apneus': 'Apneus',
            'l.actief': 'Rookt', 'l.wetteren': 'Wetteren' };
  function t(k) { if (T[k] === undefined) throw new Error('onbekende sleutel ' + k); return T[k]; }
  var JN = [{ waarde: 'ja', label_key: 'kopie.ja' }, { waarde: 'nee', label_key: 'kopie.nee' }];
  var DEF = {
    versie: '2099-01-z',
    kopie_regels: [{ id: 'onderzoek', scheiding: ' | ' }, { id: 'patient', prefix_key: 'k.pt', scheiding: ', ' }, { id: 'scores', scheiding: ' | ' },
                   { id: 'klachten', scheiding: ', ' }, { id: 'leefstijl', scheiding: ' | ' }, { id: 'medicatie' }, { id: 'vraag' }, { id: 'verwijzer', scheiding: ', ' }],
    velden: [
      { id: 'patient_naam', type: 'tekst', kopie_label: null },
      { id: 'patient_rrn', type: 'tekst', kopie_label: null },
      { id: 'geboortedatum', type: 'datum', kopie_label: '', kopie_prioriteit: 1, kopie_regel: 'patient', kopie_formaat: 'geboortedatum' },
      { id: 'geslacht', type: 'keuze', kopie_label: '', kopie_prioriteit: 1, kopie_regel: 'patient', opties: [{ waarde: 'm', kopie_key: 'o.m' }] },
      { id: 'onderzoek', type: 'keuze', kopie_label: 'k.gevraagd', kopie_prioriteit: 1, kopie_regel: 'onderzoek',
        opties: [{ waarde: 'pg', kopie_key: 'o.pg' }, { waarde: 'psg', kopie_key: 'o.psg' }] },
      { id: 'campus', type: 'keuze', kopie_label: 'k.voorkeur', kopie_prioriteit: 3, kopie_regel: 'onderzoek', opties: [{ waarde: 'w', label: 'Wetteren' }] },
      { id: 'urgentie', type: 'keuze', kopie_label: 'k.urgentie', kopie_prioriteit: 2, kopie_regel: 'onderzoek', standaard: 'normaal',
        kopie_formaat: 'niet_standaard', kopie_met: 'urgentie_toelichting', opties: [{ waarde: 'normaal', kopie_key: 'o.normaal' }, { waarde: 'verhoogd', kopie_key: 'o.verhoogd' }] },
      { id: 'urgentie_toelichting', type: 'vrije_tekst', kopie_label: null },
      { id: 'sb_s', type: 'ja_nee', groep: 'stopbang', letter: 's', kopie_label: null },
      { id: 'sb_b', type: 'ja_nee', groep: 'stopbang', letter: 'b', kopie_label: null },
      { id: 'sb', type: 'berekend', kopie_label: 'k.sb', kopie_prioriteit: 1, kopie_regel: 'scores', kopie_formaat: 'stopbang', kopie_volgorde: 1 },
      { id: 'ess', type: 'berekend', kopie_label: 'k.ess', kopie_prioriteit: 1, kopie_regel: 'scores', kopie_formaat: 'ess', kopie_volgorde: 2 },
      { id: 'bmi', type: 'berekend', kopie_label: 'k.bmi', kopie_prioriteit: 1, kopie_regel: 'scores', kopie_formaat: 'decimaal', kopie_volgorde: 3 },
      { id: 'hals', type: 'getal', kopie_label: 'k.hals', kopie_prioriteit: 2, kopie_regel: 'scores', kopie_formaat: 'cm', kopie_volgorde: 4 },
      { id: 'klachten', type: 'meerkeuze', kopie_label: 'k.klachten', kopie_prioriteit: 2, kopie_regel: 'klachten', exclusief: 'geen',
        opties: [{ waarde: 'snurken', label_key: 'l.snurken' }, { waarde: 'apneus', label_key: 'l.apneus' }, { waarde: 'geen', label_key: 'js.pdf_geen' }] },
      { id: 'stuur', type: 'ja_nee', kopie_label: 'k.stuur', kopie_prioriteit: 2, kopie_regel: 'klachten', kopie_formaat: 'indien_ja', opties: JN },
      { id: 'roken', type: 'keuze', kopie_label: 'k.roken', kopie_prioriteit: 4, kopie_regel: 'leefstijl', opties: [{ waarde: 'actief', label_key: 'l.actief' }] },
      { id: 'medicatie', type: 'vrije_tekst', kopie_label: 'k.med', kopie_prioriteit: 2, kopie_regel: 'medicatie', inkortbaar: true },
      { id: 'vraag', type: 'vrije_tekst', kopie_label: 'k.vraag', kopie_prioriteit: 1, kopie_regel: 'vraag', inkortbaar: true },
      { id: 'verwijzer', type: 'tekst', kopie_label: 'k.verwijzer', kopie_prioriteit: 1, kopie_regel: 'verwijzer' },
      { id: 'riziv', type: 'tekst', kopie_label: 'k.riziv', kopie_prioriteit: 1, kopie_regel: 'verwijzer', kopie_formaat: 'spatie' }
    ]
  };
  function data(extra) {
    var d = { patient_naam: 'JANSSENS UNIEKENAAM', patient_rrn: '68.04.12-123.45', geboortedatum: '1968-03-12', geslacht: 'm', onderzoek: 'psg', campus: 'w',
              urgentie: 'verhoogd', urgentie_toelichting: 'beroepschauffeur', sb_s: 'ja', sb_b: 'nee', sb: 6, ess: 14, bmi: 33.1, hals: '43',
              klachten: ['snurken', 'apneus'], stuur: 'ja', roken: 'actief', medicatie: 'bisoprolol, apixaban', vraag: 'OSA? Graag beoordeling.',
              verwijzer: 'dr. Test', riziv: '1-23456-78-901' };
    Object.keys(extra || {}).forEach(function (k) { d[k] = extra[k]; });
    return d;
  }
  var O = { t: t, max: 1000, maxVrij: 40, kliniek: 'Slaapkliniek X' };

  // 1. vorm en inhoud
  var r = K.genereerTekst(data(), DEF, 'nl', O), regels = r.tekst.split('\n');
  eq(regels[0], 'AANVRAAG – Slaapkliniek X [form 2099-01-z]', 'kopregel met formulierversie');
  eq(regels[1], 'Gevraagd: PSG | Voorkeur: Wetteren | Urgentie: verhoogd (beroepschauffeur)', 'onderzoeksregel');
  eq(regels[2], 'Pt: ° 12/03/1968, M', 'patiëntregel: alleen geboortedatum en geslacht');
  eq(regels[3], 'STOP-BANG 6/8 (S) | ESS 14/24 | BMI 33,1 | Hals 43 cm', 'scoreregel met decimale komma');
  eq(regels[4], 'Klachten: snurken, apneus, slaperig achter stuur', 'klachten + indien_ja-label');
  eq(regels[regels.length - 1], 'Verwijzer: dr. Test, RIZIV 1-23456-78-901', 'verwijzerregel');
  ok(r.tekst.indexOf('JANSSENS') === -1 && r.tekst.indexOf('UNIEKENAAM') === -1, 'patiëntnaam staat NIET in de kopie');
  ok(r.tekst.indexOf('68.04.12') === -1 && r.tekst.indexOf('123.45') === -1, 'rijksregisternummer staat NIET in de kopie');
  ok(!/\t|\r/.test(r.tekst), 'geen tabs of CR');
  ok(!/: *(\n|$)/.test(r.tekst) && !/\| *(\n|$)/.test(r.tekst), 'geen lege labels of hangende scheidingstekens');
  eq(r.ingekort, false, 'past binnen 1000 tekens');
  eq(r.lengte, r.tekst.length, 'lengte klopt');

  // 2. decimale punt in het Engels, komma in het Frans
  ok(K.genereerTekst(data(), DEF, 'en', O).tekst.indexOf('BMI 33.1') !== -1, 'en: decimale punt');
  ok(K.genereerTekst(data(), DEF, 'fr', O).tekst.indexOf('BMI 33,1') !== -1, 'fr: decimale komma');

  // 3. alleen ingevulde velden; standaard-urgentie zonder toelichting valt weg
  var leegD = data({ campus: '', urgentie: 'normaal', urgentie_toelichting: '', klachten: [], stuur: 'nee', roken: '', medicatie: '', hals: '' });
  var r3 = K.genereerTekst(leegD, DEF, 'nl', O);
  ok(r3.tekst.indexOf('Voorkeur') === -1 && r3.tekst.indexOf('Urgentie') === -1 && r3.tekst.indexOf('Klachten') === -1 && r3.tekst.indexOf('Medicatie') === -1, 'lege velden geven geen regel');
  ok(r3.tekst.indexOf('Hals') === -1 && r3.tekst.indexOf('slaperig achter stuur') === -1, 'leeg getal en nee-antwoord vallen weg');
  ok(K.genereerTekst(data({ klachten: ['geen'] }), DEF, 'nl', O).tekst.indexOf('Klachten: geen') !== -1, '"geen van deze" wordt "geen"');

  // 4. inkorten: hoogste prioriteit valt eerst, prioriteit 1 nooit, vrije tekst krijgt een beletselteken
  var lang = new Array(60).join('zeer lange medicatielijst ');
  var vraagLang = new Array(40).join('uitgebreide vraagstelling ');
  var r4 = K.genereerTekst(data({ medicatie: lang, vraag: vraagLang }), DEF, 'nl', { t: t, max: 400, maxVrij: 40, kliniek: 'Slaapkliniek X' });
  ok(r4.ingekort, 'te lang → ingekort');
  ok(r4.lengte <= 400, 'respecteert max_tekens (' + r4.lengte + ')');
  ok(r4.verwijderd.indexOf('roken') === 0, 'prioriteit 4 valt als eerste');
  ok(r4.verwijderd.indexOf('campus') !== -1 && r4.verwijderd.indexOf('campus') < r4.verwijderd.indexOf('medicatie'), 'prioriteit 3 valt vóór prioriteit 2');
  ['onderzoek', 'sb', 'ess', 'bmi', 'vraag', 'verwijzer', 'riziv'].forEach(function (id) { ok(r4.verwijderd.indexOf(id) === -1, 'prioriteit 1 blijft: ' + id); });
  ok(r4.tekst.indexOf('Gevraagd: PSG') !== -1 && r4.tekst.indexOf('STOP-BANG 6/8') !== -1 && r4.tekst.indexOf('Verwijzer: dr. Test') !== -1, 'kerngegevens staan er nog');
  ok(/Vraag: .{1,39}…/.test(r4.tekst), 'vraagstelling ingekort met beletselteken');
  ok(r4.tekst.split('\n').pop() === '(volledige brief als PDF beschikbaar)', 'verwijzing naar de PDF als laatste regel');
  var r5 = K.genereerTekst(data({ medicatie: lang }), DEF, 'nl', { t: t, max: 30, maxVrij: 40, kliniek: 'Slaapkliniek X' });
  ok(r5.tekst.indexOf('Gevraagd: PSG') !== -1 && r5.tekst.indexOf('RIZIV 1-23456-78-901') !== -1, 'ook bij een onhaalbare limiet blijft prioriteit 1 staan');

  // 5. hulpfuncties
  eq(K.getalTekst(33.14, 'nl', 1), '33,1', 'getalTekst nl');
  eq(K.getalTekst('43', 'de'), '43', 'getalTekst geheel');
  eq(K.getalTekst('', 'nl'), '', 'getalTekst leeg');
  eq(K.datumKort('1968-03-12'), '12/03/1968', 'datumKort');

  root.__RESULT_KOPIEER = 'OK (' + n + ' checks)';
  if (typeof console !== 'undefined' && console.log && typeof process !== 'undefined') console.log(root.__RESULT_KOPIEER);
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
