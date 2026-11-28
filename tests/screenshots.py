"""Dev only: screenshot the rendered sample issues, phone and desktop width, light and dark.

python -m brief.run --fixture        (renders run/preview*.html first)
python tests/screenshots.py          writes run/screens/<edition>-<width>-<light|dark>.png
The rendered samples are the visual reference (DESIGN_SYSTEM.md). Needs Playwright
(requirements-dev.txt), never used by the morning run.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "run" / "screens"
PREVIEWS = {"weekday": "run/preview.html", "monday": "run/preview-monday.html",
            "weekend": "run/preview-weekend.html", "birthday": "run/preview-birthday.html",
            "unavailable": "run/preview-unavailable.html"}
WIDTHS = (390, 640)
SCHEMES = ("light", "dark")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, path in PREVIEWS.items():
            for width in WIDTHS:
                for scheme in SCHEMES:
                    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
                    page.goto((ROOT / path).as_uri())
                    page.wait_for_load_state("networkidle")
                    out = OUT / f"{name}-{width}-{scheme}.png"
                    page.screenshot(path=str(out), full_page=True)
                    page.close()
                    print(out.relative_to(ROOT))
        browser.close()


if __name__ == "__main__":
    main()
