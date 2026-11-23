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


def export_page(source, destination):
    html = (ROOT / source).read_text()

    def inline_css(match):
        path = ROOT / match[1]
        css = path.read_text()

        def inline_url(asset):
            url = asset[1].strip().strip('\"\'')
            if url.startswith(('#', 'data:', 'https:', 'http:')):
                return asset[0]
            relative = (path.parent / url).relative_to(ROOT)
            return f'url("{data_url(relative)}")'

        css = re.sub(r'url\(([^)]+)\)', inline_url, css)
        return f"<style>{css}</style>"

    html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', inline_css, html)
    html = re.sub(r'\s*<link rel="preload"[^>]+>', "", html)
    # Preserve deferred script order after the DOM in the standalone exports.
    deferred = []

    def inline_deferred(match):
        deferred.append(f'<script>{(ROOT / match[1]).read_text()}</script>')
        return ""

    html = re.sub(r'<script src="([^"]+)" defer></script>', inline_deferred, html)
    html = html.replace("</body>", "\n".join(deferred) + "\n</body>")
    html = html.replace('<script src="scripts/theme-init.js"></script>',
                        f'<script>{(ROOT / "scripts/theme-init.js").read_text()}</script>')
    html = re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)', lambda m: m[1] + data_url(m[2]), html)
    html = re.sub(r'(<a\b[^>]*\bhref=")(images/[^"#]+)', lambda m: m[1] + data_url(m[2]), html)
    html = html.replace('href="events.html', 'href="events-preview.html')
    html = html.replace('href="index.html', 'href="monet-preview.html')
    output = ROOT / "preview" / destination
    output.parent.mkdir(exist_ok=True)
    output.write_text(html)
    print(f"Offline preview: {output}")


def main():
    export_page("index.html", "monet-preview.html")
    export_page("events.html", "events-preview.html")
    print("Open either HTML in a browser. Keep both files together for navigation; no server is required.")


if __name__ == "__main__":
    main()
