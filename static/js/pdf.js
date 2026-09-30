/* pdf.js — de verwijsbrief als PDF, volledig in de browser (jsPDF, vendor/). Geen netwerk. */
(function (root) {
  'use strict';

  // Helvetica (WinAnsi) kent geen ≥, → of ·: vervang ze, anders staat er een leeg vakje.
  function ascii(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/≥/g, '>=').replace(/≤/g, '<=').replace(/→/g, '->').replace(/·/g, '-')
      .replace(/–/g, '-').replace(/—/g, '-').replace(/[‘’]/g, "'").replace(/[“”„]/g, '"');
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

  /**
   * data: het object uit form.js (verzamel()); t: vertaalfunctie; opties: { jsPDF, vandaag }.
   * Geeft de bestandsnaam terug. Gooit als jsPDF ontbreekt.
   */
  function maak(data, t, opties) {
    opties = opties || {};
    var JsPdf = opties.jsPDF || (root.jspdf && root.jspdf.jsPDF);
    if (!JsPdf) throw new Error('jsPDF ontbreekt');
    var doc = new JsPdf({ unit: 'mm', format: 'a4' });
    var marge = 18, breedte = 210 - 2 * marge, y = marge, regelH = 5.2;

    function nieuwePaginaAlsNodig(h) {
      if (y + h > 297 - marge - 12) { doc.addPage(); y = marge; }
    }
    function kop(txt) {
      nieuwePaginaAlsNodig(12);
      y += 3;
      doc.setFont('helvetica', 'bold'); doc.setFontSize(11.5); doc.setTextColor(26, 58, 143);
      doc.text(ascii(txt), marge, y); y += 2;
      doc.setDrawColor(26, 58, 143); doc.line(marge, y, marge + breedte, y); y += 4.5;
      doc.setTextColor(0, 0, 0);
    }
    function regel(label, waarde) {
      var w = ascii(waarde);
      if (w === '') w = ascii(t('js.pdf_geen'));
      doc.setFont('helvetica', 'bold'); doc.setFontSize(9.5);
      var labelTxt = ascii(label) + ':';
      var lijnen = doc.splitTextToSize(w, breedte - 52);
      nieuwePaginaAlsNodig(regelH * lijnen.length);
      doc.text(labelTxt, marge, y);
      doc.setFont('helvetica', 'normal');
      doc.text(lijnen, marge + 50, y);
      y += regelH * lijnen.length;
    }
    function alinea(txt) {
      doc.setFont('helvetica', 'normal'); doc.setFontSize(9.5);
      var lijnen = doc.splitTextToSize(ascii(txt), breedte);
      nieuwePaginaAlsNodig(regelH * lijnen.length);
      doc.text(lijnen, marge, y); y += regelH * lijnen.length;
    }

    var stempel = datumStempel(opties.vandaag);
    doc.setFont('helvetica', 'bold'); doc.setFontSize(15); doc.setTextColor(26, 58, 143);
    doc.text(ascii(t('js.pdf_kop')), marge, y); y += 7;
    doc.setFont('helvetica', 'normal'); doc.setFontSize(9.5); doc.setTextColor(0, 0, 0);
    doc.text(ascii(t('js.pdf_datum')) + ': ' + stempel.iso, marge, y); y += 4;

    kop(t('js.pdf_verwijzer'));
    regel(t('js.pdf_verwijzer'), data.verwijzer.naam);
    regel(t('js.pdf_riziv'), data.verwijzer.riziv);
    regel(t('js.pdf_adres'), data.verwijzer.adres);
    regel(t('js.pdf_tel'), data.verwijzer.tel);

    kop(t('js.pdf_patient'));
    regel(t('js.pdf_patient'), data.patient.naam);
    regel(t('js.pdf_geboortedatum'), data.patient.geboortedatum);
    regel(t('js.pdf_geslacht'), data.patient.geslachtLabel);
    regel(t('js.pdf_rrn'), data.patient.rrn);

    kop(t('js.pdf_onderzoek'));
    regel(t('js.pdf_onderzoek'), data.onderzoek.label);
    regel(t('js.pdf_campus'), data.onderzoek.campusLabel);
    regel(t('js.pdf_urgentie'), data.urgentie.label + (data.urgentie.toelichting ? ' - ' + data.urgentie.toelichting : ''));

    kop(t('aanvraag.sectie_klinisch'));
    regel(t('js.pdf_klachten'), data.klachten.join(', '));
    regel(t('js.pdf_antropometrie'),
      (data.lengte || '-') + ' cm / ' + (data.gewicht || '-') + ' kg / BMI ' + (data.bmi === null ? '-' : data.bmi) + ' / ' + (data.hals || '-') + ' cm');
    var essTxt = data.ess.totaal === null ? t('js.pdf_geen') : (data.ess.totaal + '/24' + (data.ess.interpretatie ? ' (' + data.ess.interpretatie + ')' : ''));
    regel(t('js.pdf_ess'), essTxt);
    if (data.ess.totaal !== null) regel(t('js.pdf_ess_items'), data.ess.items.map(function (v, i) { return (i + 1) + ':' + v; }).join('  '));
    regel(t('js.pdf_stopbang'), data.stopbang.totaal + '/8  (' + data.stopbang.itemsTekst + ')');
    regel(t('js.pdf_comorbiditeit'), data.comorbiditeit.join(', '));
    regel(t('js.pdf_medicatie'), data.medicatie);
    regel(t('js.pdf_eerder'), (data.eerder.ja ? t('js.pdf_ja') : t('js.pdf_nee')) + (data.eerder.toelichting ? ' - ' + data.eerder.toelichting : ''));

    kop(t('js.pdf_vraagstelling'));
    alinea(data.vraagstelling);

    kop(t('js.pdf_keuzehulp'));
    alinea(data.keuzehulpTekst);
    alinea(t('aanvraag.keuzehulp_arts'));

    nieuwePaginaAlsNodig(30);
    y += 8;
    doc.setFont('helvetica', 'bold'); doc.setFontSize(9.5);
    doc.text(ascii(t('js.pdf_handtekening')) + ':', marge, y);
    doc.setFont('helvetica', 'normal');
    doc.text(ascii(data.verwijzer.naam) + ' - ' + stempel.iso, marge + 50, y); y += 14;
    doc.line(marge + 50, y, marge + 130, y);

    var paginas = doc.getNumberOfPages();
    for (var p = 1; p <= paginas; p++) {
      doc.setPage(p);
      doc.setFont('helvetica', 'normal'); doc.setFontSize(7.5); doc.setTextColor(90, 90, 90);
      doc.text(ascii(t('js.pdf_voettekst')) + '   ' + p + '/' + paginas, marge, 297 - 10);
    }

    var naam = bestandsnaam(t('js.pdf_bestandsnaam'), opties.vandaag);
    if (!opties.nietOpslaan) doc.save(naam);
    return naam;
  }

  var Pdf = { maak: maak, bestandsnaam: bestandsnaam, ascii: ascii };
  if (typeof module !== 'undefined' && module.exports) module.exports = Pdf;
  root.Pdf = Pdf;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
