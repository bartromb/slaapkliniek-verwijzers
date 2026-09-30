/* tests/test_scores.js — draait in de browser (tests/test_scores.html), in Node (node tests/test_scores.js)
   en in V8 via tests/test_build.py. Zet __RESULT op 'OK' of gooit bij de eerste fout. */
(function (root) {
  'use strict';
  var S = root.Scores || (typeof require === 'function' ? require('../static/js/scores.js') : null);
  if (!S) throw new Error('Scores niet geladen');
  var n = 0;
  function eq(a, b, wat) { n++; if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error('FOUT ' + wat + ': ' + JSON.stringify(a) + ' != ' + JSON.stringify(b)); }

  // BMI
  eq(S.bmi(180, 81), 25, 'bmi 180/81');
  eq(S.bmi('170', '110.5'), 38.2, 'bmi 170/110.5');
  eq(S.bmi('', 80), null, 'bmi zonder lengte');
  eq(S.bmi(180, 0), null, 'bmi gewicht 0');
  eq(S.bmi(20, 80), null, 'bmi onzinnige lengte');

  // leeftijd en geboortedatum
  eq(S.leeftijd('1970-06-15', '2026-06-14'), 55, 'leeftijd dag voor verjaardag');
  eq(S.leeftijd('1970-06-15', '2026-06-15'), 56, 'leeftijd op verjaardag');
  eq(S.leeftijd('abc'), null, 'leeftijd ongeldig');
  eq(S.geboortedatumGeldig('1970-06-15', '2026-01-01'), true, 'gd geldig');
  eq(S.geboortedatumGeldig('2030-01-01', '2026-01-01'), false, 'gd toekomst');
  eq(S.geboortedatumGeldig('1850-01-01', '2026-01-01'), false, 'gd te oud');
  eq(S.geboortedatumGeldig('2025-02-30', '2026-01-01'), false, 'gd niet-bestaande dag');
  eq(S.geboortedatumGeldig('', '2026-01-01'), false, 'gd leeg');

  // ESS
  eq(S.essTotaal([0, 1, 2, 3, 0, 1, 2, 3]), 12, 'ess som');
  eq(S.essTotaal(['3', '3', '3', '3', '3', '3', '3', '3']), 24, 'ess max als strings');
  eq(S.essTotaal([0, 1, 2, null, 0, 1, 2, 3]), null, 'ess item ontbreekt');
  eq(S.essTotaal([0, 1, 2, 4, 0, 1, 2, 3]), null, 'ess item > 3');
  eq(S.essTotaal([0, 1, 2]), null, 'ess te weinig items');
  eq(S.essInterpretatie(10), 'normaal', 'ess 10 normaal');
  eq(S.essInterpretatie(11), 'verhoogd', 'ess 11 verhoogd');
  eq(S.essInterpretatie(null), null, 'ess null');

  // STOP-BANG afgeleid + totaal
  eq(S.stopbangAfgeleid({ bmi: 35.1, leeftijd: 51, hals: 40.5, geslacht: 'm' }), { b: true, a: true, n: true, g: true }, 'sb alles net boven');
  eq(S.stopbangAfgeleid({ bmi: 35, leeftijd: 50, hals: 40, geslacht: 'v' }), { b: false, a: false, n: false, g: false }, 'sb grenzen zijn exclusief');
  eq(S.stopbangAfgeleid({}), { b: false, a: false, n: false, g: false }, 'sb leeg');
  eq(S.stopbangTotaal({ s: true, t: true, o: false, p: true, b: true, a: false, n: true, g: true }), 6, 'sb totaal 6');
  eq(S.stopbangTotaal({}), 0, 'sb totaal leeg');

  // keuzehulp
  var naarPsg = ['hartfalen', 'cva', 'copd', 'neuromusculair', 'opioiden', 'andere_slaapstoornis'];
  eq(S.keuzehulp({ stopbang: 5, comorbiditeiten: [], drempel: 5, naarPsg: naarPsg }).advies, 'pg', 'keuze pg op drempel');
  eq(S.keuzehulp({ stopbang: 4, comorbiditeiten: [], drempel: 5, naarPsg: naarPsg }), { advies: 'psg', reden: 'laag' }, 'keuze psg laag');
  eq(S.keuzehulp({ stopbang: 8, comorbiditeiten: ['vkf'], drempel: 5, naarPsg: naarPsg }).advies, 'pg', 'vkf stuurt niet naar psg');
  eq(S.keuzehulp({ stopbang: 8, comorbiditeiten: ['vkf', 'copd'], drempel: 5, naarPsg: naarPsg }), { advies: 'psg', reden: 'comorbiditeit', comorbiditeiten: ['copd'] }, 'copd stuurt naar psg');
  eq(S.keuzehulp({ stopbang: null, comorbiditeiten: [], drempel: 5, naarPsg: naarPsg }).reden, 'onvolledig', 'keuze onvolledig');

  // RIZIV
  eq(S.rizivGeldig('1-23456-78-901'), true, 'riziv net');
  eq(S.rizivNormaliseer('12345678901'), '1-23456-78-901', 'riziv elf cijfers');
  eq(S.rizivNormaliseer(' 1 23456 78 901 '), '1-23456-78-901', 'riziv met spaties');
  eq(S.rizivGeldig('1-23456-78-90'), false, 'riziv te kort');
  eq(S.rizivGeldig('a-23456-78-901'), false, 'riziv letters');
  eq(S.rizivGeldig(''), false, 'riziv leeg');

  root.__RESULT = 'OK (' + n + ' checks)';
  if (typeof console !== 'undefined' && console.log && typeof process !== 'undefined') console.log(root.__RESULT);
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
