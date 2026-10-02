#!/usr/bin/env python3
"""tools/record_demo.py — geleide demo-video van het hele verwijsproces (Playwright + ffmpeg).

    .venv-claude/bin/python tools/record_demo.py --lang nl \
        --chrome ~/.cache/cft/chrome-linux64/chrome --out videos/

Neemt op tegen de live site (of --base-url), met fictieve gegevens (geen patiëntdata),
on-screen bijschriften en een getekende cursor. Schrijft <lang>.webm en <lang>.mp4
(libx264, yuv420p) en de gegenereerde PDF als controle. Vereist: playwright, imageio-ffmpeg,
pymupdf (PDF-pagina in beeld) en een Chrome/Chromium-executable.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1366, 768

CAPTIONS = {
    "nl": {
        "intro": "Slaaponderzoek aanvragen via verwijzers.slaapkliniek.be — zo werkt het",
        "info": "Stap 1 — Polygrafie of polysomnografie? De info-pagina helpt kiezen.",
        "form": "Stap 2 — Vul de verwijsbrief in. Alles blijft in uw browser.",
        "verwijzer": "Uw gegevens als verwijzer, met RIZIV-nummer.",
        "patient": "De patiënt: naam, geboortedatum, geslacht. Rijksregisternummer is optioneel.",
        "onderzoek": "Gevraagd onderzoek, voorkeurcampus en urgentie.",
        "klinisch": "Klachten en antropometrie: de BMI wordt meteen berekend.",
        "ess": "Epworth Sleepiness Scale: acht items, totaal automatisch.",
        "stopbang": "STOP-BANG: BMI, leeftijd, halsomtrek en geslacht zijn al afgeleid.",
        "keuzehulp": "De keuzehulp geeft een suggestie. De slaaparts beslist.",
        "pdf": "Stap 3 — Maak de verwijsbrief (PDF). Niets wordt naar een server gestuurd.",
        "pdf_toon": "De PDF: klaar om als bijlage toe te voegen.",
        "voorgeschiedenis": "Comorbiditeit en voorgeschiedenis: het label \u201cconventie\u201d toont wat vermoedelijk gevraagd wordt.",
        "kopie": "Kopieer als tekst: compact, zonder naam van de patiënt, klaar om in Consult te plakken.",
        "volgende": "Drie routes: Consult, eHealthBox (zodra actief) of telefonisch.",
        "consult": "Stap 4 — Het stappenplan voor Consult, met terugvaloptie.",
        "login": "“Inloggen op Consult” gaat rechtstreeks naar het portaal: itsme of eID.",
        "einde": "Klaar: verwijsbrief als bijlage, afspraak in de agenda van de Slaapkliniek.",
    },
    "en": {
        "intro": "Requesting a sleep study via verwijzers.slaapkliniek.be — how it works",
        "info": "Step 1 — Polygraphy or polysomnography? The info page helps you choose.",
        "form": "Step 2 — Fill in the referral letter. Everything stays in your browser.",
        "verwijzer": "Your details as referring physician, with RIZIV/INAMI number.",
        "patient": "The patient: name, date of birth, sex. National register number is optional.",
        "onderzoek": "Requested study, preferred site and urgency.",
        "klinisch": "Symptoms and anthropometry: the BMI is calculated immediately.",
        "ess": "Epworth Sleepiness Scale: eight items, total calculated automatically.",
        "stopbang": "STOP-BANG: BMI, age, neck circumference and sex are already derived.",
        "keuzehulp": "The decision aid suggests a study type. The sleep physician decides.",
        "pdf": "Step 3 — Create the referral letter (PDF). Nothing is sent to any server.",
        "pdf_toon": "The PDF: ready to attach.",
        "voorgeschiedenis": "Comorbidity and history: the \u201cconvention\u201d label shows what will probably be required.",
        "kopie": "Copy as text: compact, without the patient's name, ready to paste into Consult.",
        "volgende": "Three routes: Consult, eHealthBox (once active) or by telephone.",
        "consult": "Step 4 — The step-by-step guide for Consult, with a fallback option.",
        "login": "\u201cLog in to Consult\u201d goes straight to the portal: itsme or eID.",
        "einde": "Done: referral letter attached, appointment in the Sleep Clinic's schedule.",
    },
    "fr": {
        "intro": "Demander un examen du sommeil via verwijzers.slaapkliniek.be — comment ça marche",
        "info": "Étape 1 — Polygraphie ou polysomnographie ? La page d'info aide à choisir.",
        "form": "Étape 2 — Remplissez la lettre de renvoi. Tout reste dans votre navigateur.",
        "verwijzer": "Vos coordonnées de prescripteur, avec le numéro INAMI.",
        "patient": "Le patient : nom, date de naissance, sexe. Le numéro de registre national est facultatif.",
        "onderzoek": "Examen demandé, site préféré et urgence.",
        "klinisch": "Plaintes et anthropométrie : l'IMC est calculé immédiatement.",
        "ess": "Échelle de somnolence d'Epworth : huit items, total automatique.",
        "stopbang": "STOP-BANG : IMC, âge, tour de cou et sexe sont déjà déduits.",
        "keuzehulp": "L'aide à la décision propose un examen. Le médecin du sommeil décide.",
        "pdf": "Étape 3 — Créez la lettre de renvoi (PDF). Rien n'est envoyé à un serveur.",
        "pdf_toon": "Le PDF : prêt à joindre en annexe.",
        "voorgeschiedenis": "Comorbidités et antécédents : le label « convention » indique ce qui sera probablement demandé.",
        "kopie": "Copier comme texte : compact, sans le nom du patient, prêt à coller dans Consult.",
        "volgende": "Trois voies : Consult, eHealthBox (dès qu'elle est active) ou par téléphone.",
        "consult": "Étape 4 — Le guide pas à pas pour Consult, avec une solution de repli.",
        "login": "« Se connecter à Consult » mène directement au portail : itsme ou eID.",
        "einde": "Terminé : lettre de renvoi en annexe, rendez-vous dans l'agenda de la Clinique du sommeil.",
    },
    "de": {
        "intro": "Schlafuntersuchung anfragen über verwijzers.slaapkliniek.be — so funktioniert es",
        "info": "Schritt 1 — Polygraphie oder Polysomnographie? Die Infoseite hilft bei der Wahl.",
        "form": "Schritt 2 — Überweisungsschreiben ausfüllen. Alles bleibt in Ihrem Browser.",
        "verwijzer": "Ihre Angaben als Zuweiser, mit RIZIV/INAMI-Nummer.",
        "patient": "Der Patient: Name, Geburtsdatum, Geschlecht. Die Nationalregisternummer ist optional.",
        "onderzoek": "Gewünschte Untersuchung, bevorzugter Standort und Dringlichkeit.",
        "klinisch": "Beschwerden und Anthropometrie: der BMI wird sofort berechnet.",
        "ess": "Epworth Sleepiness Scale: acht Items, Gesamtwert automatisch.",
        "stopbang": "STOP-BANG: BMI, Alter, Halsumfang und Geschlecht sind bereits abgeleitet.",
        "keuzehulp": "Die Entscheidungshilfe macht einen Vorschlag. Der Schlafmediziner entscheidet.",
        "pdf": "Schritt 3 — Überweisungsschreiben (PDF) erstellen. Nichts wird an einen Server gesendet.",
        "pdf_toon": "Das PDF: bereit als Anhang.",
        "voorgeschiedenis": "Komorbidität und Vorgeschichte: das Label \u201eKonvention\u201c zeigt, was voraussichtlich verlangt wird.",
        "kopie": "Als Text kopieren: kompakt, ohne Patientennamen, bereit zum Einfügen in Consult.",
        "volgende": "Drei Wege: Consult, eHealthBox (sobald aktiv) oder telefonisch.",
        "consult": "Schritt 4 — Die Schritt-für-Schritt-Anleitung für Consult, mit Ausweichmöglichkeit.",
        "login": "\u201eBei Consult anmelden\u201c führt direkt zum Portal: itsme oder eID.",
        "einde": "Fertig: Überweisungsschreiben als Anhang, Termin im Kalender der Schlafklinik.",
    },
}

DEMO = {
    "verwijzer_naam": "Dr. An Voorbeeld", "verwijzer_riziv": "1-23456-78-901",
    "verwijzer_adres": "Dorpsstraat 1, 9230 Wetteren", "verwijzer_tel": "09 123 45 67",
    "patient_naam": "Voorbeeld Jan", "patient_geboortedatum": "1968-04-12",
    "lengte": "178", "gewicht": "112", "hals": "43",
    "medicatie": "Amlodipine 5 mg",
}
VRAAGSTELLING = {
    "nl": "Vermoeden van obstructief slaapapneu; graag polygrafie.",
    "en": "Suspected obstructive sleep apnoea; polygraphy requested.",
    "fr": "Suspicion d'apnées obstructives du sommeil ; polygraphie souhaitée.",
    "de": "Verdacht auf obstruktive Schlafapnoe; Polygraphie erbeten.",
}


class Demo:
    def __init__(self, page, lang):
        self.page, self.lang = page, lang
        self.cx, self.cy = W // 2, H // 2

    # ── overlays (context draait met bypass_csp, anders blokkeert de CSP de stijl) ──
    def _ensure_overlay(self):
        self.page.evaluate("""() => {
          if (!document.getElementById('demo-cursor')) {
            const c = document.createElement('div'); c.id = 'demo-cursor';
            Object.assign(c.style, {position:'fixed', width:'22px', height:'22px', borderRadius:'50%',
              background:'rgba(26,58,143,.55)', border:'3px solid #fff', boxShadow:'0 0 0 2px rgba(26,58,143,.8)',
              zIndex: 2147483647, pointerEvents:'none', transform:'translate(-50%,-50%)', transition:'left .05s, top .05s'});
            document.body.appendChild(c);
          }
          if (!document.getElementById('demo-caption')) {
            const d = document.createElement('div'); d.id = 'demo-caption';
            Object.assign(d.style, {position:'fixed', left:'50%', bottom:'28px', transform:'translateX(-50%)',
              maxWidth:'86%', padding:'14px 22px', background:'rgba(18,41,106,.94)', color:'#fff',
              font:'500 21px/1.35 system-ui, sans-serif', borderRadius:'12px', zIndex: 2147483646,
              boxShadow:'0 8px 30px rgba(0,0,0,.35)', opacity:'0', transition:'opacity .35s', pointerEvents:'none'});
            document.body.appendChild(d);
          }
        }""")
        self.page.evaluate("([x, y]) => { const c = document.getElementById('demo-cursor'); c.style.left = x + 'px'; c.style.top = y + 'px'; }", [self.cx, self.cy])

    def caption(self, key, hold=3.2):
        self._ensure_overlay()
        text = CAPTIONS[self.lang][key]
        self.page.evaluate("t => { const d = document.getElementById('demo-caption'); d.textContent = t; d.style.opacity = '1'; }", text)
        time.sleep(hold)

    def caption_off(self):
        self.page.evaluate("() => { const d = document.getElementById('demo-caption'); if (d) d.style.opacity = '0'; }")

    # ── beweging ────────────────────────────────────────────────────────────
    def move_to(self, selector, steps=22):
        loc = self.page.locator(selector).first
        loc.scroll_into_view_if_needed()
        time.sleep(0.25)
        self._ensure_overlay()
        box = loc.bounding_box()
        x, y = box["x"] + min(box["width"] / 2, 160), box["y"] + box["height"] / 2
        for i in range(1, steps + 1):
            nx, ny = self.cx + (x - self.cx) * i / steps, self.cy + (y - self.cy) * i / steps
            self.page.mouse.move(nx, ny)
            self.page.evaluate("([x, y]) => { const c = document.getElementById('demo-cursor'); c.style.left = x + 'px'; c.style.top = y + 'px'; }", [nx, ny])
            time.sleep(0.012)
        self.cx, self.cy = x, y
        return loc

    def click(self, selector, pause=0.5):
        loc = self.move_to(selector)
        self.page.evaluate("() => { const c = document.getElementById('demo-cursor'); c.style.background = 'rgba(163,18,26,.7)'; setTimeout(() => c.style.background = 'rgba(26,58,143,.55)', 180); }")
        loc.click()
        time.sleep(pause)

    def type_into(self, selector, text, delay=28):
        self.click(selector, pause=0.15)
        self.page.locator(selector).first.press_sequentially(text, delay=delay)
        time.sleep(0.25)

    def scroll(self, y, dwell=1.2):
        self.page.evaluate("y => window.scrollTo({top: y, behavior: 'smooth'})", y)
        time.sleep(dwell)


def run(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    lang = args.lang
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome or None, args=["--no-sandbox", "--disable-gpu"])
        ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(out),
                                  record_video_size={"width": W, "height": H}, bypass_csp=True,
                                  locale={"nl": "nl-BE", "fr": "fr-BE", "en": "en-GB", "de": "de-DE"}[lang],
                                  accept_downloads=True)
        ctx.grant_permissions(["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        d = Demo(page, lang)
        base = args.base_url.rstrip("/")

        # 1. info
        page.goto(f"{base}/{lang}/", wait_until="networkidle")
        d.caption("intro", 3.5)
        d.caption("info", 2.5); d.scroll(420, 2.2); d.scroll(900, 2.0); d.caption_off(); d.scroll(0, 0.8)

        # 2. formulier
        d.click("a.knop.primair[href$='/aanvraag/']", pause=0.8)
        page.wait_for_selector("#verwijsbrief")
        d.caption("form", 2.8); d.caption_off()
        d.caption("verwijzer", 0.4)
        d.type_into("#verwijzer_naam", DEMO["verwijzer_naam"])
        d.type_into("#verwijzer_riziv", DEMO["verwijzer_riziv"])
        d.type_into("#verwijzer_adres", DEMO["verwijzer_adres"])
        d.type_into("#verwijzer_tel", DEMO["verwijzer_tel"])
        d.caption("patient", 0.4)
        d.type_into("#patient_naam", DEMO["patient_naam"])
        d.click("#patient_geboortedatum", pause=0.1); page.fill("#patient_geboortedatum", DEMO["patient_geboortedatum"]); time.sleep(0.4)
        d.click("input[name='patient_geslacht'][value='m']")
        d.caption("onderzoek", 0.4)
        d.click("input[name='onderzoek'][value='pg']")
        d.click("#campus", pause=0.2); page.select_option("#campus", index=1); time.sleep(0.4)
        d.caption("klinisch", 0.4)
        for k in ("snurken", "apneus", "slaperigheid"):
            d.click(f"input[name='klachten'][value='{k}']", pause=0.2)
        d.click("input[name='slaperig_stuur'][value='nee']", pause=0.2)
        d.type_into("#lengte", DEMO["lengte"]); d.type_into("#gewicht", DEMO["gewicht"]); d.type_into("#hals", DEMO["hals"])
        d.move_to("#bmi"); time.sleep(1.0)
        d.caption("ess", 0.4)
        for i, w in enumerate([2, 2, 1, 2, 2, 1, 1, 2], start=1):
            d.click(f"input[name='ess_{i}'][value='{w}']", pause=0.15)
        d.move_to("#ess_totaal"); time.sleep(1.0)
        d.caption("stopbang", 0.4)
        for k in ("s", "t", "o", "p"):
            d.click(f"input[name='sb_{k}'][value='ja']", pause=0.2)
        d.move_to("#stopbang_totaal"); time.sleep(1.2)
        d.caption("voorgeschiedenis", 0.4)
        d.click("input[name='cv'][value='hypertensie']", pause=0.2)
        d.click("input[name='dm2'][value='nee']", pause=0.2)
        d.click("input[name='eerder_onderzoek'][value='nee']", pause=0.2)
        d.click("input[name='cpap_mra'][value='nee']", pause=0.2)
        d.type_into("#medicatie", DEMO["medicatie"])
        d.type_into("#vraagstelling", VRAAGSTELLING[lang])
        d.caption("keuzehulp", 0.3); d.move_to("#keuzehulp_tekst"); time.sleep(2.6); d.caption_off()

        # 3. kopieertekst en PDF
        d.caption("kopie", 0.5)
        d.click("#knop_kopieer", pause=0.4)
        d.move_to("#kopie_voorbeeld"); time.sleep(3.2); d.caption_off()
        d.caption("pdf", 0.6)
        with page.expect_download() as dl:
            d.click("#knop_pdf", pause=0.3)
        pdf_path = out / f"verwijsbrief_demo_{lang}.pdf"
        dl.value.save_as(str(pdf_path))
        time.sleep(1.2)
        d.move_to("#bezorgen_titel"); d.caption("volgende", 3.0); d.caption_off()

        # 3b. de PDF zelf in beeld (pagina 1 als afbeelding)
        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path)); pix = doc[0].get_pixmap(dpi=96)
            png = out / f"verwijsbrief_demo_{lang}_p1.png"; pix.save(str(png))
            page.goto(png.resolve().as_uri()); time.sleep(0.4)
            page.evaluate("() => { document.body.style.background = '#e9edf5'; const img = document.querySelector('img'); if (img) { img.style.display='block'; img.style.margin='0 auto'; img.style.height='100vh'; img.style.boxShadow='0 6px 30px rgba(0,0,0,.35)'; } }")
            d.cx, d.cy = W // 2, H // 2
            d.caption("pdf_toon", 4.0); d.caption_off()
        except Exception as e:  # noqa: BLE001
            print("PDF-weergave overgeslagen:", e)

        # 4. Consult
        page.goto(f"{base}/{lang}/consult/", wait_until="networkidle")
        d.cx, d.cy = W // 2, H // 2
        d.caption("consult", 2.5); d.scroll(380, 2.4); d.scroll(0, 0.8); d.caption_off()
        d.caption("login", 0.5)
        loc = d.move_to("a.knop.primair"); time.sleep(1.0)
        page.evaluate("a => a.removeAttribute('target')", loc.element_handle())
        loc.click()
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3.0)
        d.caption("einde", 3.5)
        video = page.video
        ctx.close(); browser.close()
        webm_tmp = Path(video.path())
    webm = out / f"{lang}.webm"
    shutil.move(str(webm_tmp), webm)
    mp4 = out / f"{lang}.mp4"
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-preset", "slow", "-crf", "24",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(mp4)], check=True)
    print("klaar:", webm, mp4, f"{mp4.stat().st_size/1e6:.1f} MB", "| pdf:", pdf_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://verwijzers.slaapkliniek.be")
    ap.add_argument("--lang", default="nl", choices=sorted(CAPTIONS))
    ap.add_argument("--chrome", default=None, help="pad naar chrome/chromium (anders Playwrights eigen)")
    ap.add_argument("--out", default="videos")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
