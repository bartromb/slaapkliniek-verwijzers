/* pdf.js — de verwijsbrief als PDF, volledig in de browser (jsPDF, vendor/). Geen netwerk.
   Het model komt uit form.js en volgt de secties van config/velden.json:
   { kop, secties: [{titel, regels: [{label, waarde}]}], vrij: [{titel, tekst}], verwijzerNaam, versie, url } */
(function (root) {
  'use strict';

  // Helvetica (WinAnsi) kent geen ≥, → of ·: vervang ze, anders staat er een leeg vakje.
  function ascii(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/→/g, '->').replace(/·/g, '-')
      .replace(/–/g, '-').replace(/—/g, '-').replace(/[‘’]/g, "'").replace(/[“”„]/g, '"')
      .replace(/…/g, '...');
  }

  function datumStempel(d) {
    d = d ? (d instanceof Date ? d : new Date(d)) : new Date();
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return { iso: d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate()),
             compact: '' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) };
  }

  /** Bestandsnaam zonder patiëntnaam: <prefix>_<YYYYMMDD>.pdf */
  function bestandsnaam(prefix, d) {
    return String(prefix || 'verwijsbrief').replace(/[^A-Za-z0-9_-]/g, '_') + '_' + datumStempel(d).compact + '.pdf';
  }

  /** model: zie kop van dit bestand; t: vertaalfunctie; opties: { jsPDF, vandaag, nietOpslaan }. Geeft de bestandsnaam. */
  function maak(model, t, opties) {
    opties = opties || {};
    var JsPdf = opties.jsPDF || (root.jspdf && root.jspdf.jsPDF);
    if (!JsPdf) throw new Error('jsPDF ontbreekt');
    var doc = new JsPdf({ unit: 'mm', format: 'a4' });
    var marge = 17, breedte = 210 - 2 * marge, y = marge, regelH = 4.6;

    function nieuwePaginaAlsNodig(h) {
      if (y + h > 297 - marge - 12) { doc.addPage(); y = marge; }
    }
    function kop(txt) {
      nieuwePaginaAlsNodig(12);
      y += 1.8;
      doc.setFont('helvetica', 'bold'); doc.setFontSize(10.5); doc.setTextColor(226, 0, 21);
      doc.text(ascii(txt), marge, y); y += 1.8;
      doc.setDrawColor(226, 0, 21); doc.line(marge, y, marge + breedte, y); y += 4.0;
      doc.setTextColor(0, 0, 0);
    }
    function regel(label, waarde) {
      var w = ascii(waarde);
      if (w === '') w = '-';
      doc.setFont('helvetica', 'bold'); doc.setFontSize(9.2);
      // Een lang label breekt binnen zijn eigen kolom af; de waarde start op dezelfde regel.
      var labelLijnen = doc.splitTextToSize(ascii(label) + ':', 58);
      doc.setFont('helvetica', 'normal');
      var lijnen = doc.splitTextToSize(w, breedte - 64);
      var n = Math.max(lijnen.length, labelLijnen.length);
      nieuwePaginaAlsNodig(regelH * n);
      doc.setFont('helvetica', 'bold');
      doc.text(labelLijnen, marge, y);
      doc.setFont('helvetica', 'normal');
      doc.text(lijnen, marge + 62, y);
      y += regelH * n;
    }
    function alinea(txt) {
      doc.setFont('helvetica', 'normal'); doc.setFontSize(9.2);
      var lijnen = doc.splitTextToSize(ascii(txt), breedte);
      nieuwePaginaAlsNodig(regelH * lijnen.length);
      doc.text(lijnen, marge, y); y += regelH * lijnen.length;
    }

    var stempel = datumStempel(opties.vandaag);
    doc.setFont('helvetica', 'bold'); doc.setFontSize(15); doc.setTextColor(31, 31, 31);
    doc.text(ascii(model.kop), marge, y); y += 6.5;
    doc.setFont('helvetica', 'normal'); doc.setFontSize(9.2); doc.setTextColor(0, 0, 0);
    doc.text(ascii(t('js.pdf_datum')) + ': ' + stempel.iso, marge, y); y += 3.5;

    (model.secties || []).forEach(function (s) {
      if (!s.regels || !s.regels.length) return;
      kop(s.titel);
      s.regels.forEach(function (r) { regel(r.label, r.waarde); });
    });
    (model.vrij || []).forEach(function (b) {
      if (!b.tekst) return;
      kop(b.titel);
      String(b.tekst).split('\n').forEach(alinea);
    });

    nieuwePaginaAlsNodig(22);
    y += 6;
    doc.setFont('helvetica', 'bold'); doc.setFontSize(9.2);
    doc.text(ascii(t('js.pdf_handtekening')) + ':', marge, y);
    doc.setFont('helvetica', 'normal');
    doc.text(ascii(model.verwijzerNaam || '') + ' - ' + stempel.iso, marge + 62, y); y += 11;
    doc.setDrawColor(120, 120, 120); doc.line(marge + 62, y, marge + 142, y);

    var paginas = doc.getNumberOfPages();
    var voet = ascii(t('js.pdf_voettekst')) + '  |  ' + ascii(t('js.pdf_formulierversie')) + ' ' + ascii(model.versie || '') + (model.url ? '  |  ' + ascii(model.url) : '');
    for (var p = 1; p <= paginas; p++) {
      doc.setPage(p);
      doc.setFont('helvetica', 'normal'); doc.setFontSize(7.2); doc.setTextColor(90, 90, 90);
      doc.text(doc.splitTextToSize(voet + '   ' + p + '/' + paginas, breedte), marge, 297 - 11);
    }

    var naam = bestandsnaam(t('js.pdf_bestandsnaam'), opties.vandaag);
    if (!opties.nietOpslaan) doc.save(naam);
    if (opties.geefUitvoer) return { naam: naam, uitvoer: doc.output() };   // alleen voor tests
    return naam;
  }

  var Pdf = { maak: maak, bestandsnaam: bestandsnaam, ascii: ascii };
  if (typeof module !== 'undefined' && module.exports) module.exports = Pdf;
  root.Pdf = Pdf;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
