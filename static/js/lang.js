/* lang.js — alleen op de root-pagina: stuur door naar de browsertaal als die ondersteund is.
   Geen cookie, geen opslag; de meta-refresh op de pagina valt terug op /nl/. */
(function () {
  'use strict';
  var talen = ['nl', 'fr', 'en', 'de'];
  var voorkeur = (navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'nl']);
  for (var i = 0; i < voorkeur.length; i++) {
    var code = String(voorkeur[i] || '').slice(0, 2).toLowerCase();
    if (talen.indexOf(code) !== -1) {
      var basis = document.documentElement.getAttribute('data-base-path') || '/';
      window.location.replace(basis + code + '/');
      return;
    }
  }
})();
