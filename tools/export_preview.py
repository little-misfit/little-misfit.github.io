"""Export a portable, offline preview without publishing or modifying the website."""
import base64
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def data_url(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Asset outside site: {relative}")
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def main():
    html = (ROOT / "index.html").read_text()
    css = (ROOT / "index_css.css").read_text()
    css = re.sub(r'url\("([^"]+)"\)', lambda m: f'url("{data_url(m[1])}")', css)
    html = html.replace('<link rel="stylesheet" href="index_css.css">', f"<style>{css}</style>")
    html = re.sub(r'\s*<link rel="preload"[^>]+>', "", html)
    # The deferred UI script belongs after the DOM in this standalone export.
    html = html.replace('<script src="scripts/site.js" defer></script>', "")
    html = html.replace("</body>", f'<script>{(ROOT / "scripts/site.js").read_text()}</script>\n</body>')
    html = html.replace('<script src="scripts/theme-init.js"></script>',
                        f'<script>{(ROOT / "scripts/theme-init.js").read_text()}</script>')
    html = re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)', lambda m: m[1] + data_url(m[2]), html)
    output = ROOT / "preview" / "monet-preview.html"
    output.parent.mkdir(exist_ok=True)
    output.write_text(html)
    print(f"Offline preview: {output}")
    print("Open this HTML in a browser. No server or network connection is required.")


if __name__ == "__main__":
    main()
