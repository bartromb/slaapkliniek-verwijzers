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
        "volgende": "Volgende stap: de afspraak zelf boeken in Nexuzhealth Consult.",
        "consult": "Stap 4 — Het stappenplan voor Consult, met terugvaloptie.",
        "login": "“Inloggen op Consult” gaat rechtstreeks naar het portaal: itsme of eID.",
        "einde": "Klaar: verwijsbrief als bijlage, afspraak in de agenda van de Slaapkliniek.",
    },
}

DEMO = {
    "verwijzer_naam": "Dr. An Voorbeeld", "verwijzer_riziv": "1-23456-78-901",
    "verwijzer_adres": "Dorpsstraat 1, 9230 Wetteren", "verwijzer_tel": "09 123 45 67",
    "patient_naam": "Voorbeeld Jan", "patient_geboortedatum": "1968-04-12",
    "lengte": "178", "gewicht": "112", "hals": "43",
    "medicatie": "Amlodipine 5 mg", "vraagstelling": "Vermoeden van obstructief slaapapneu; graag polygrafie.",
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
            d.click(f"input[name='klacht'][value='{k}']", pause=0.25)
        d.type_into("#lengte", DEMO["lengte"]); d.type_into("#gewicht", DEMO["gewicht"]); d.type_into("#hals", DEMO["hals"])
        d.move_to("#bmi"); time.sleep(1.2)
        d.caption("ess", 0.4)
        for i, w in enumerate([2, 2, 1, 2, 2, 1, 1, 2], start=1):
            d.click(f"input[name='ess_{i}'][value='{w}']", pause=0.18)
        d.move_to("#ess_totaal"); time.sleep(1.2)
        d.caption("stopbang", 0.4)
        for k in ("s", "t", "o", "p"):
            d.click(f"input[name='sb_{k}']", pause=0.25)
        d.move_to("#sb_totaal"); time.sleep(1.4)
        d.type_into("#medicatie", DEMO["medicatie"])
        d.type_into("#vraagstelling", DEMO["vraagstelling"])
        d.caption("keuzehulp", 0.3); d.move_to("#keuzehulp_tekst"); time.sleep(3.0); d.caption_off()

        # 3. PDF
        d.caption("pdf", 0.6)
        with page.expect_download() as dl:
            d.click("#knop_pdf", pause=0.3)
        pdf_path = out / f"verwijsbrief_demo_{lang}.pdf"
        dl.value.save_as(str(pdf_path))
        time.sleep(1.2)
        d.move_to("#volgende"); d.caption("volgende", 3.0); d.caption_off()

        # 3b. de PDF zelf in beeld (pagina 1 als afbeelding)
        try:
            import fitz  # pymupdf
            doc = fitz.open(str(pdf_path)); pix = doc[0].get_pixmap(dpi=96)
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
