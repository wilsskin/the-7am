"""Local runner for development. Never sends anything.

python -m brief.run --fixture [weekday|monday|weekend|birthday|unavailable|all]
    Renders the sample issues in tests/fixtures/issues/ to run/preview-<name>.html
    (run/preview.html is the weekday one).
python -m brief.run --dry-run
    Runs the collectors, then renders run/content.json + run/calendar.json (if present)
    to run/preview.html. Lenient, so it renders whatever is there.
"""
import argparse
import shutil
from datetime import datetime
from pathlib import Path

from brief import render
from brief.collect.__main__ import collect
from brief.common import ET, ROOT, RUN_DIR, now_et

FIXTURES = ROOT / "tests" / "fixtures" / "issues"
PREVIEW_ICONS = "../templates/icons/{}.png"   # relative to run/
# Placeholder images for the sample memes, preview only (the email hotlinks real ones).
MEME_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{h}"><rect width="100%" height="100%" fill="#F0F0F0"/>'
            '<text x="50%" y="50%" font-family="-apple-system,Helvetica" font-size="28" fill="#6F6F6F" '
            'text-anchor="middle" dominant-baseline="middle">Meme {i}</text></svg>')


def render_fixture(name: str) -> dict:
    work = RUN_DIR / "fixtures" / name
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(FIXTURES / name, work)
    date = (work / "data.json").read_text().split('"date": "')[1][:10]
    now = datetime.fromisoformat(f"{date}T06:41:00").replace(tzinfo=ET)
    meta = render.render(work, lenient=True, icon_src="../" + PREVIEW_ICONS, now=now, out_name="preview")
    html = (work / "preview.html").read_text()
    for i in range(1, 7):
        svg = work / f"meme{i}.svg"
        svg.write_text(MEME_SVG.format(h=[1200, 952, 1000, 800][i % 4], i=i))
        html = html.replace(f"https://i.redd.it/sample{i}.jpg", f"fixtures/{name}/meme{i}.svg")
    html = html.replace("../" + PREVIEW_ICONS.split("{")[0], PREVIEW_ICONS.split("{")[0])
    out = RUN_DIR / ("preview.html" if name == "weekday" else f"preview-{name}.html")
    out.write_text(html)
    shutil.copy(work / "preview.txt", out.with_suffix(".txt"))
    print(f"{out.relative_to(ROOT)}: {meta['bytes']:,} bytes, icons {meta['icons']}, missing {meta['missing'] or 'none'}")
    for w in meta["warnings"]:
        print("  warning:", w)
    return meta


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--fixture", nargs="?", const="all")
    g.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    RUN_DIR.mkdir(exist_ok=True)
    if a.fixture:
        names = sorted(x.name for x in FIXTURES.iterdir()) if a.fixture == "all" else [a.fixture]
        for n in names:
            render_fixture(n)
    else:
        import json
        data = collect(now_et())
        (RUN_DIR / "data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        meta = render.render(RUN_DIR, lenient=True, icon_src=PREVIEW_ICONS, out_name="preview")
        print(f"run/preview.html: {meta['bytes']:,} bytes; warnings: {len(meta['warnings'])}")


if __name__ == "__main__":
    main()
