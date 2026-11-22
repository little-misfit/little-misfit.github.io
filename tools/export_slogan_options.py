"""Create a self-contained font comparison without changing the homepage."""
import base64
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "preview"
CACHE = OUTPUT / "slogan-fonts"
SLOGAN = "Perfection is reason made sensual."
FONTS = [
    ("A", "La Belle Aurore", "Expressive handwriting", "labelleaurore", None),
    ("B", "Allura", "Fluid & understated", "allura", "https://fonts.gstatic.com/s/allura/v23/9oRPNYsQpS4zjuA_iwgW.woff2"),
    ("C", "Parisienne", "Soft & romantic", "parisienne", "https://fonts.gstatic.com/s/parisienne/v14/E21i_d3kivvAkxhLEVZpQyhwDw.woff2"),
    ("D", "Sacramento", "Fine-line & relaxed", "sacramento", "https://fonts.gstatic.com/s/sacramento/v17/buEzpo6gcdjy0EiZMBUG4C0f_Q.woff2"),
    ("E", "Italianno", "Slender & flowing", "italianno", "https://fonts.gstatic.com/s/italianno/v18/dg4n_p3sv6gCJkwzT6RXiJwo.woff2"),
    ("F", "Pinyon Script", "Formal calligraphy", "pinyonscript", "https://fonts.gstatic.com/s/pinyonscript/v24/6xKpdSJbL9-e9LuoeQiDRQR8WOXaOg.woff2"),
    ("G", "Caveat", "Natural & spontaneous", "caveat", "https://fonts.gstatic.com/s/caveat/v23/WnznHAc5bAfYB2QRah7pcpNvOx-pjfJ9eIWpYQ.woff2"),
    ("H", "Nothing You Could Do", "Selected · open & informal", "nothingyoucoulddo", "https://fonts.gstatic.com/s/nothingyoucoulddo/v21/oY1B8fbBpaP5OX3DtrRYf_Q2BPB1SnfZb3OOnVs.woff2"),
]


def download(url, path):
    if not path.exists():
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=30) as response:
            payload = response.read()
        path.write_bytes(payload)
    return path


def embedded(path, mime):
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def font_face(name, path):
    return f'@font-face{{font-family:"{name}";src:url("{embedded(path, "font/woff2")}") format("woff2");font-weight:400;font-style:normal;font-display:swap;}}'


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    css = [font_face("Manrope", ROOT / "fonts/manrope-latin.woff2")]
    rows, licenses = [], []
    for letter, name, note, slug, url in FONTS:
        if url:
            font = download(url, CACHE / f"{slug}.woff2")
            license_file = download(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{slug}/OFL.txt", CACHE / f"OFL-{slug}.txt")
        else:
            font = ROOT / "fonts/la-belle-aurore-latin.woff2"
            license_file = ROOT / "fonts/OFL-La-Belle-Aurore.txt"
        css.append(font_face(name, font))
        rows.append(f'''<article class="font-row" aria-labelledby="font-{letter}">
          <header class="font-label"><span class="letter">{letter}</span><div><h2 id="font-{letter}">{name}</h2><p>{note}</p></div></header>
          <div class="sample day" style="--font:'{name}'"><span class="theme-label">Day</span><p>{SLOGAN}</p></div>
          <div class="sample night" style="--font:'{name}'"><span class="theme-label">Night</span><p>{SLOGAN}</p></div>
        </article>''')
        licenses.append(f'<details><summary>{name}</summary><pre>{escape(license_file.read_text())}</pre></details>')
    licenses.append('<details><summary>Manrope</summary><pre>' + escape((ROOT / 'fonts/OFL-Manrope.txt').read_text()) + '</pre></details>')
    template = (ROOT / "tools/slogan_options.html").read_text()
    html = template.replace("{{FONT_CSS}}", "\n".join(css)).replace("{{ROWS}}", "\n".join(rows)).replace("{{LICENSES}}", "\n".join(licenses))
    destination = OUTPUT / "slogan-options.html"
    destination.write_text(html)
    print(f"Offline font comparison: {destination}")


if __name__ == "__main__":
    main()
