/* Toont het resultaat van test_scores.js op de testpagina (aparte file: geen inline scripts). */
(function () {
  var el = document.getElementById('uit');
  el.textContent = window.__RESULT || 'FOUT: geen resultaat (zie console)';
  el.style && (el.className = window.__RESULT ? 'melding ok' : 'melding');
})();
