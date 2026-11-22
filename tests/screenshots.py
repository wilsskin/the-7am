"""Dev only: screenshot the rendered samples next to the reference mockups and diff them.

python tests/screenshots.py          (run python -m brief.run --fixture first)
Writes run/screens/<edition>-<width>-<light|dark>.png and ref-... for each reference, and
prints how many pixels differ above the Meme roundup (memes are placeholders in the
mockups and images in the render, so they always differ).
Needs Playwright (requirements-dev.txt), never used by the morning run.
"""
import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "run" / "screens"
PAIRS = {"weekday": ("templates/reference_issue.html", "run/preview.html"),
         "monday": ("templates/reference_monday.html", "run/preview-monday.html"),
         "weekend": ("templates/reference_weekend.html", "run/preview-weekend.html"),
         "birthday": (None, "run/preview-birthday.html"),
         "unavailable": (None, "run/preview-unavailable.html")}
WIDTHS = (390, 640)
SCHEMES = ("light", "dark")

DIFF_JS = """async ([a, b, limit]) => {
  const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = src; });
  const [ia, ib] = await Promise.all([load(a), load(b)]);
  const w = Math.min(ia.width, ib.width), h = Math.min(limit, ia.height, ib.height);
  const px = img => { const c = document.createElement('canvas'); c.width = w; c.height = h;
    const x = c.getContext('2d'); x.drawImage(img, 0, 0); return x.getImageData(0, 0, w, h).data; };
  const da = px(ia), db = px(ib); let diff = 0, firstY = -1;
  for (let i = 0; i < da.length; i += 4) {
    if (Math.abs(da[i]-db[i]) + Math.abs(da[i+1]-db[i+1]) + Math.abs(da[i+2]-db[i+2]) > 30) {
      diff++; if (firstY < 0) firstY = Math.floor(i / 4 / w); } }
  return {diff, total: w * h, firstY, heightA: ia.height, heightB: ib.height};
}"""


def shoot(browser, path, width, scheme, name):
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme, device_scale_factor=1)
    page.goto((ROOT / path).as_uri())
    page.wait_for_load_state("networkidle")
    memes_y = page.evaluate("""() => { const h = [...document.querySelectorAll('h2')].find(e => e.textContent === 'Meme roundup');
                                       return h ? h.getBoundingClientRect().top + window.scrollY : document.body.scrollHeight; }""")
    out = OUT / f"{name}-{width}-{scheme}.png"
    page.screenshot(path=str(out), full_page=True)
    page.close()
    return out, int(memes_y)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        canvas = browser.new_page()
        for name, (ref, new) in PAIRS.items():
            for width in WIDTHS:
                for scheme in SCHEMES:
                    new_png, limit = shoot(browser, new, width, scheme, name)
                    if not ref:
                        print(f"{name:11} {width} {scheme:5}  {new_png.name}")
                        continue
                    ref_png, ref_limit = shoot(browser, ref, width, scheme, "ref-" + name)
                    uri = lambda f: "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()
                    r = canvas.evaluate(DIFF_JS, [uri(ref_png), uri(new_png), min(limit, ref_limit)])
                    pct = 100 * r["diff"] / r["total"]
                    where = f", first difference at y={r['firstY']}px" if r["diff"] else ""
                    print(f"{name:11} {width} {scheme:5}  {pct:6.3f}% of pixels differ above the memes{where}")
        browser.close()


if __name__ == "__main__":
    main()
