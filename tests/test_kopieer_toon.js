/* Toont het resultaat van test_kopieer.js op de testpagina (aparte file: geen inline scripts). */
(function () {
  var el = document.getElementById('uit');
  el.textContent = window.__RESULT_KOPIEER || 'FOUT: geen resultaat (zie console)';
  el.className = window.__RESULT_KOPIEER ? 'melding ok' : 'melding';
})();
